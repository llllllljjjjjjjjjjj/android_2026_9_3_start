// dy_hook22.js — Charles 抓包辅助（QUIC 降级 + 证书校验观测/兜底）
//
// 背景（抖音 38.0.0 实测）：
//   - 网络栈 = libsscronet.so（ByteDance ttnet 魔改 Chromium），默认开 QUIC(HTTP/3, UDP 443)
//   - QUIC 无视 HTTP 代理 → 不降级则核心 API 流量全部直连绕过 Charles
//   - 证书校验 = com.ttnet.org.chromium.net.X509Util.verifyServerCertificates
//     （Java 层, native 经 JNI 回调；无 CertificatePinner, 无 network_security_config
//     → 只验系统证书链 + isKnownRoot 查 /system/etc/security/cacerts 文件名）
//
// 功能：
//   1) QUIC 降级：native Cronet_EngineParams_enable_quic_set 强制 false
//      + Java ExperimentalCronetEngine$Builder.enableQuic 强制 false
//      → 流量回落 TCP+TLS(ALPN h2) → 走系统代理 → Charles
//   2) 证书观测：打印每个 TLS 握手 host / status / knownRoot
//      → status=0 && knownRoot=true 说明系统证书装对了
//      → status=-2 = 证书不受信任（没进系统库/装错）
//      → status=0 && knownRoot=false = 证书在系统库但文件名 hash 不对（见 isKnownRoot 逻辑）
//   3) 证书兜底：BYPASS=true 时校验失败也返回 OK(knownRoot=true)
//      → 证书彻底装不上时 Charles 仍能解密（先用默认 false 诊断，别直接开）
//   4) 按应用代理注入（不碰全局 http_proxy，零额外软件直连 Charles）：
//      - hook ProxyChangeListener.proxySettingsChanged（初始配置与 PROXY_CHANGE 广播的唯一漏斗）
//      - hook ConnectivityManager.getDefaultProxy（全栈读代理入口，消除时序竞态）
//      用法：REPL 里先 rpc.exports.setproxy(true, "<PC-IP>", 8888) 再 %resume
//      （Kitsunebi 按应用 VPN 模式则保持 FORCE=false，流量由 tun 接管无需注入）
//
// 用法（真机 Pixel 4 / f1657 16.5.7 / .venv-frida-16.5.7）：
//   adb forward tcp:27042 tcp:27042
//   .venv-frida-16.5.7\Scripts\frida.exe -U -f com.ss.android.ugc.aweme -l hooks/dy_hook22.js
//   （或复用 scripts/run_hook.py 的 spawn+attach 模式）
//   抖音冷启动 40-90s，libsscronet 后加载 —— 脚本自带定时重挂，不用管时序
//
// RPC: setbypass(true/false) 运行时切换兜底开关

var BYPASS = false; // ★证书装好后保持 false；确认装不上再改 true

// 按应用代理注入（默认关：Kitsunebi 按应用 VPN 转发模式不需要）
// 开启方式见 RPC setproxy / 或直接改下面的 enabled
var FORCE = { enabled: false, host: "127.0.0.1", port: 1080 };

// ---------------- 1. QUIC 降级 ----------------

var quicArmed = false;
function armNativeQuic() {
    if (quicArmed) return;
    var p = Module.findExportByName("libsscronet.so", "Cronet_EngineParams_enable_quic_set");
    if (!p) return; // 模块还没加载，等下一轮
    try {
        Interceptor.attach(p, {
            onEnter: function (args) {
                // void Cronet_EngineParams_enable_quic_set(EngineParamsPtr self, bool enable_quic)
                args[1] = ptr(0);
            }
        });
        quicArmed = true;
        console.log("[quic] native Cronet_EngineParams_enable_quic_set armed → QUIC 已强制关闭");
    } catch (e) {
        console.log("[quic] native attach fail: " + e.message);
    }
}
armNativeQuic();
setInterval(armNativeQuic, 2000); // libsscronet 冷启动后才映射，轮询补挂

// ---------------- 2. Java 层 ----------------

var VERIFY_CLS = {
    "com.ttnet.org.chromium.net.X509Util": "com.ttnet.org.chromium.net.AndroidCertVerifyResult", // 主网络栈(API)
    "com.p781ss.videoarch.live.ttquic.X509Util": "com.p781ss.videoarch.live.ttquic.AndroidCertVerifyResult" // 直播QUIC栈
};

Java.perform(function () {

    // 2a. Java Builder QUIC 关闭（C-API 之外的另一条引擎构建路径）
    var tryBuilderHook = function () {
        if (tryBuilderHook.done) return;
        try {
            var B = Java.use("com.ttnet.org.chromium.net.ExperimentalCronetEngine$Builder");
            B.enableQuic.overload("boolean").implementation = function (x) {
                console.log("[quic] Builder.enableQuic(" + x + ") → 强制 false");
                return this.enableQuic(false);
            };
            tryBuilderHook.done = true;
            console.log("[quic] Java Builder.enableQuic armed");
        } catch (e) { /* 类未加载，等 loadClass 触发 */ }
    };
    tryBuilderHook();

    // 2b. 证书校验观测 + 兜底
    var hooked = {};
    function hookVerify(cls) {
        if (hooked[cls]) return;
        var acr = VERIFY_CLS[cls];
        try {
            var X = Java.use(cls);
            X.verifyServerCertificates.overload("[[B", "java.lang.String", "java.lang.String")
                .implementation = function (certs, authType, host) {
                    var r = this.verifyServerCertificates(certs, authType, host);
                    var st = r.getStatus();
                    var kr = r.isIssuedByKnownRoot();
                    console.log("[crt] " + host + " auth=" + authType +
                                " status=" + st + " knownRoot=" + kr +
                                (BYPASS && st !== 0 ? "  →BYPASS" : ""));
                    if (BYPASS && st !== 0) {
                        try {
                            var CF = Java.use("java.security.cert.CertificateFactory").getInstance("X.509");
                            var list = Java.use("java.util.ArrayList").$new();
                            for (var i = 0; i < certs.length; i++) {
                                var bais = Java.use("java.io.ByteArrayInputStream").$new(certs[i]);
                                list.add(CF.generateCertificate(bais));
                            }
                            return Java.use(acr).$new(0, true, list); // status=0, knownRoot=true, 原证书链
                        } catch (e2) {
                            console.log("[crt] BYPASS forge fail: " + e2.message);
                        }
                    }
                    return r;
                };
            hooked[cls] = true;
            console.log("[crt] hooked " + cls + " (BYPASS=" + BYPASS + ")");
        } catch (e) { /* 类未加载 */ }
    }
    var TARGETS = Object.keys(VERIFY_CLS);
    TARGETS.forEach(hookVerify);

    // X509Util 按需加载（Cronet 初始化时才 loadclass）→ 挂 loadClass 触发 + 定时兜底
    try {
        var CL = Java.use("java.lang.ClassLoader");
        CL.loadClass.overload("java.lang.String").implementation = function (n) {
            var r = this.loadClass(n);
            if (VERIFY_CLS[n]) hookVerify(n);
            if (n === "com.ttnet.org.chromium.net.ExperimentalCronetEngine$Builder") tryBuilderHook();
            return r;
        };
    } catch (e) {
        console.log("[crt] loadClass hook fail: " + e.message);
    }
    setInterval(function () {
        TARGETS.forEach(hookVerify);
        tryBuilderHook();
    }, 5000);

    // 2c. 按应用代理注入（不碰全局 http_proxy；Kitsunebi 按应用 VPN 模式保持关闭）
    var proxyArmed = {};
    function armProxyHook() {
        if (proxyArmed.done) return;
        try {
            var PCL = Java.use("com.ttnet.org.chromium.net.ProxyChangeListener");
            var PC = Java.use("com.ttnet.org.chromium.net.ProxyChangeListener$ProxyConfig");

            // 漏斗点：初始配置(getProxyConfig)与 PROXY_CHANGE 广播最终都调这里
            PCL.proxySettingsChanged.implementation = function (cfg) {
                if (FORCE.enabled) {
                    try {
                        var forced = PC.$new(FORCE.host, FORCE.port, "", Java.array("java.lang.String", []));
                        if (cfg === null || String(cfg.mHost.value) !== FORCE.host || cfg.mPort.value !== FORCE.port) {
                            console.log("[proxy] inject " + FORCE.host + ":" + FORCE.port +
                                        " (原配置 " + (cfg ? cfg.mHost.value + ":" + cfg.mPort.value : "null") + ")");
                        }
                        return this.proxySettingsChanged(forced);
                    } catch (e) {
                        console.log("[proxy] inject fail: " + e.message);
                    }
                }
                return this.proxySettingsChanged(cfg);
            };

            // 防 App 侧 setEnabled(false) 关掉代理支持（含 hook 挂上之前就已关闭的情况）
            var origSetEnabled = PCL.setEnabled;
            PCL.setEnabled.implementation = function (z) {
                if (FORCE.enabled && !z) console.log("[proxy] setEnabled(false) 被拦截 → true");
                return FORCE.enabled ? origSetEnabled.call(this, true) : origSetEnabled.call(this, z);
            };
            if (FORCE.enabled && !PCL.sEnabled.value) {
                PCL.sEnabled.value = true;
                console.log("[proxy] sEnabled 静态字段复位 true");
            }

            proxyArmed.done = true;
            console.log("[proxy] ProxyChangeListener hooked (FORCE=" + FORCE.enabled + ")");
        } catch (e) { /* 类未加载，等下一轮 */ }
    }
    armProxyHook();
    setInterval(armProxyHook, 5000);

    // 2d. ConnectivityManager.getDefaultProxy 伪造：App 内所有读取系统代理的地方
    //     （Cronet/OkHttp/libcore 全栈）统一返回注入的代理，消除
    //     "首轮 proxySettingsChanged 早于 hook 挂载" 的时序竞态
    var cmArmed = {};
    function armCMHook() {
        if (cmArmed.done) return;
        try {
            var CM = Java.use("android.net.ConnectivityManager");
            CM.getDefaultProxy.implementation = function () {
                if (FORCE.enabled) {
                    return Java.use("android.net.ProxyInfo").buildDirectProxy(FORCE.host, FORCE.port);
                }
                return this.getDefaultProxy();
            };
            cmArmed.done = true;
            console.log("[proxy] ConnectivityManager.getDefaultProxy armed");
        } catch (e) { /* 类未加载，等下一轮 */ }
    }
    armCMHook();
    setInterval(armCMHook, 5000);
});

// ---------------- 3. RPC ----------------

rpc.exports = {
    setbypass: function (v) {
        BYPASS = !!v;
        return "BYPASS=" + BYPASS;
    },
    // setproxy(enabled, host, port) — 按应用代理注入
    //   Kitsunebi 本地口:  setproxy(true, "127.0.0.1", <kitsunebi端口>)
    //   直连 Charles:     setproxy(true, "<PC-IP>", 8888)
    //   Kitsunebi 按应用 VPN 转发: 保持 setproxy(false) —— 流量由 tun 接管，无需注入
    setproxy: function (enabled, host, port) {
        FORCE.enabled = !!enabled;
        if (typeof host === "string" && host) FORCE.host = host;
        if (typeof port === "number" && port > 0) FORCE.port = port;
        return "FORCE=" + FORCE.enabled + " " + FORCE.host + ":" + FORCE.port;
    },
    status: function () {
        return {
            bypass: BYPASS,
            quicArmed: quicArmed,
            verifyHooked: Object.keys(hooked || {}).length,
            proxy: FORCE
        };
    }
};

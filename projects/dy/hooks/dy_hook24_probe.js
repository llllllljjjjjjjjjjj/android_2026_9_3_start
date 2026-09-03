// dy_hook24_probe.js v4 — 上游门卫探针（libttboringssl.so 的 verify 回调）
//
// 背景：amemv.com（评论 API）走 sscronet 主栈，不经过 VCN 的 DoVerifyV2（那只是视频网络）。
//       它的 pin 检查 = BoringSSL custom_verify 回调（libttboringssl.so 提供）。
// 本探针：
//   1) hook SSL_CTX_set_custom_verify / SSL_set_custom_verify / SSL_CTX_set_verify 注册点
//      → 记录"谁"注册了"什么"回调（backtrace）
//   2) 包装每个 custom_verify 回调：记录 主机名(SNI) + 返回值
//      → 返回值 0 = 拒绝！当场抓 amemv.com 被拒的调用链
//   3) RPC forge(true)：对 API 主机强制回调返回 1（通过）= 绕过 pin
//
// 用法：
//   adb forward tcp:27042 tcp:27042
//   .venv-frida-16.5.7\Scripts\frida.exe -H 127.0.0.1:27042 -f com.ss.android.ugc.aweme \
//       -l D:\reserve_agent\skills-portable-test\projects\dy\hooks\dy_hook24_probe.js

var FORGE = false;
var armed = false;

var API_RE = /amemv|qishui|snssdk|bytedance|douyin\.com|iesdouyin|zjcdn|byteimg|bytegoofy/;

var getServername = null;
var wrapped = {};     // 已包装的回调地址去重
var stats = { regs: 0, cbCalls: 0, fails: 0 };

function backtraceStr(ctx, n) {
    try {
        var bt = Thread.backtrace(ctx, Backtracer.ACCURATE);
        var parts = [];
        for (var i = 0; i < bt.length && i < (n || 5); i++) {
            var a = bt[i];
            var m = Process.findModuleByAddress(a);
            if (m) parts.push(m.name + "+0x" + a.sub(m.base).toString(16));
            else parts.push(a.toString());
        }
        return parts.join(" <- ");
    } catch (e) { return "(bt err)"; }
}

function hostOf(ssl) {
    try {
        if (!getServername || ssl.isNull()) return "(no ssl)";
        var p = getServername(ssl, 0);
        if (p.isNull()) return "(no SNI)";
        return p.readCString();
    } catch (e) { return "(err:" + e.message + ")"; }
}

// 包装 custom_verify 回调：签名 int (*)(SSL*, uint8_t* out_alert)
function wrapCustomCb(cb, tag) {
    if (cb.isNull() || wrapped[cb.toString()]) return;
    wrapped[cb.toString()] = true;
    try {
        Interceptor.attach(cb, {
            onEnter: function (args) {
                this.ssl = args[0];
                this.alert = args[1];
                this.host = hostOf(this.ssl);
            },
            onLeave: function (ret) {
                stats.cbCalls++;
                var r = ret.toInt32();
                var h = this.host;
                if (r === 0) stats.fails++;
                var isApi = API_RE.test(h);
                if (isApi || r === 0) {
                    console.log("[cb] " + tag + " host=" + h + " ret=" + r +
                                (r === 0 ? "  ←拒绝!" : ""));
                    if (isApi && r === 0) {
                        console.log("[cb] 拒绝现场 BT: " + backtraceStr(this.context, 8));
                    }
                }
                if (FORGE && isApi) {
                    ret.replace(1);
                    try { if (this.alert && !this.alert.isNull()) this.alert.writeU8(0); } catch (e) {}
                    console.log("[cb] " + h + " 结果被 forge 为通过");
                }
            }
        });
    } catch (e) {
        console.log("[cb] wrap fail " + tag + " " + cb + " : " + e.message);
    }
}

function arm() {
    if (armed) return;
    var b = Process.findModuleByName("libttboringssl.so");
    if (!b) return;

    // SSL_get_servername → 从 ssl 结构里读 SNI 主机名
    try {
        var gs = Module.findExportByName("libttboringssl.so", "SSL_get_servername");
        if (gs) {
            getServername = new NativeFunction(gs, 'pointer', ['pointer', 'int']);
        }
    } catch (e) { }

    // 注册点 1：SSL_CTX_set_custom_verify(ctx, cb) —— 主通道 pin 注册处
    try {
        Interceptor.attach(b.base.add(0x49dac), {
            onEnter: function (args) {
                stats.regs++;
                var ctx = args[0], cb = args[1];
                var m = Process.findModuleByAddress(cb);
                var who = m ? m.name + "+0x" + cb.sub(m.base).toString(16) : String(cb);
                console.log("[reg] SSL_CTX_set_custom_verify ctx=" + ctx + " cb=" + who +
                            "  BT: " + backtraceStr(this.context, 4));
                wrapCustomCb(cb, "custom");
            }
        });
    } catch (e) { console.log("[reg] custom_verify attach fail: " + e.message); }

    // 注册点 2：SSL_set_custom_verify(ssl, cb) —— 单连接级
    try {
        Interceptor.attach(b.base.add(0x49db8), {
            onEnter: function (args) {
                stats.regs++;
                var ssl = args[0], cb = args[1];
                var m = Process.findModuleByAddress(cb);
                var who = m ? m.name + "+0x" + cb.sub(m.base).toString(16) : String(cb);
                console.log("[reg] SSL_set_custom_verify ssl=" + ssl + " cb=" + who +
                            "  host=" + hostOf(ssl));
                wrapCustomCb(cb, "custom-per-ssl");
            }
        });
    } catch (e) { console.log("[reg] ssl_set_custom attach fail: " + e.message); }

    // 注册点 3：SSL_CTX_set_verify(ctx, mode, cb) —— 经典模式（也包一下，以防走这条）
    try {
        Interceptor.attach(b.base.add(0x50810), {
            onEnter: function (args) {
                stats.regs++;
                var cb = args[2];
                if (cb.isNull()) return;
                var m = Process.findModuleByAddress(cb);
                var who = m ? m.name + "+0x" + cb.sub(m.base).toString(16) : String(cb);
                console.log("[reg] SSL_CTX_set_verify ctx=" + args[0] + " mode=" + args[1] +
                            " cb=" + who + "  BT: " + backtraceStr(this.context, 4));
            }
        });
    } catch (e) { console.log("[reg] set_verify attach fail: " + e.message); }

    armed = true;
    console.log("[probe] libttboringssl 门卫注册点已全部武装 (FORGE=" + FORGE + ")");
}

// QUIC 降级（保留）
var quicArmed = false;
function armQuic() {
    if (quicArmed) return;
    var p = Module.findExportByName("libsscronet.so", "Cronet_EngineParams_enable_quic_set");
    if (!p) return;
    try {
        Interceptor.attach(p, {
            onEnter: function (args) { args[1] = ptr(0); }
        });
        quicArmed = true;
        console.log("[quic] native enable_quic_set armed → QUIC 强制关闭");
    } catch (e) { console.log("[quic] attach fail: " + e.message); }
}

arm();
armQuic();
setInterval(function () { arm(); armQuic(); }, 2000);

// 心跳
setInterval(function () {
    if (armed) {
        console.log("[beat] 注册 " + stats.regs + " 次 / 回调执行 " + stats.cbCalls +
                    " 次 / 拒绝 " + stats.fails + " 次 (FORGE=" + FORGE + ")");
    }
}, 30000);

rpc.exports = {
    forge: function (v) {
        FORGE = !!v;
        return "FORGE=" + FORGE + " (API 主机的 verify 回调结果强制为通过)";
    },
    status: function () {
        return { armed: armed, forge: FORGE, quic: quicArmed, stats: stats };
    }
};

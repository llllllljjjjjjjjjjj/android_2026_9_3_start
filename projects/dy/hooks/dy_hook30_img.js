// dy_hook30_img.js — FORGE v10 图片域名扩展版（基于 dy_hook30_probe.js）
// 在标准 FORGE（API 主机）基础上，把图片 CDN 域名也加入绕过范围：
//   douyinpic / ecombdimg / ecombdstatic / bytednsdoc / pstatp / douyinstatic / jinritemai
// 用法（spawn）:
//   .venv-frida-16.5.7\Scripts\frida.exe -H 127.0.0.1:27042 -f com.ss.android.ugc.aweme -l dy_hook30_img.js
var FORGE = true;
var AUTOCLEAR = true;
var armed = false;

var API_RE = /amemv|qishui|snssdk|bytedance|douyin\.com|iesdouyin|zjcdn|byteimg|bytegoofy|douyinpic|ecombdimg|ecombdstatic|bytednsdoc|pstatp|douyinstatic|jinritemai/;

var getServername = null;
var getSSLCTX = null;
var errClear = null;
var wrapped = {};
var stats = { hs: 0, cbCalls: 0, forged: 0 };

function hostOf(ssl) {
    try {
        if (!getServername || ssl.isNull()) return "(no ssl)";
        var p = getServername(ssl, 0);
        if (p.isNull()) return "(no SNI)";
        return p.readCString();
    } catch (e) { return "(err)"; }
}

function whereIs(a) {
    var m = Process.findModuleByAddress(a);
    return m ? m.name + "+0x" + a.sub(m.base).toString(16) : String(a);
}

function wrapCustomCb(cb, tag) {
    if (cb.isNull() || wrapped[cb.toString()]) return;
    var m = Process.findModuleByAddress(cb);
    if (m && m.name === "libvcn.so") return;
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
                var isApi = API_RE.test(h);
                if (isApi && r === 1 && FORGE) {
                    ret.replace(0);
                    stats.forged++;
                    try { if (this.alert && !this.alert.isNull()) this.alert.writeU8(0); } catch (e) {}
                    console.log("[forge] " + h + " 拒绝(1) → 通过(0)");
                }
                if (isApi && AUTOCLEAR && errClear) {
                    try { errClear(); } catch (e) {}
                }
            }
        });
    } catch (e) {
        console.log("[cb] wrap fail " + tag + ": " + e.message);
    }
}

function armCert() {
    if (armed) return;
    var b = Process.findModuleByName("libttboringssl.so");
    var c = Process.findModuleByName("libttcrypto.so");
    var s = Process.findModuleByName("libsscronet.so");
    if (!b || !c || !s) return;
    try {
        getServername = new NativeFunction(b.base.add(0x49d6c), 'pointer', ['pointer', 'int']);
        getSSLCTX = new NativeFunction(b.base.add(0x4a638), 'pointer', ['pointer']);
        errClear = new NativeFunction(c.base.add(0xb6014), 'void', []);
    } catch (e) { console.log("[cert] natives init fail: " + e.message); return; }

    try {
        Interceptor.attach(b.base.add(0x486c0), {
            onEnter: function (args) {
                this.ssl = args[0];
                try {
                    var ctx = getSSLCTX(this.ssl);
                    if (!ctx.isNull()) wrapCustomCb(ctx.add(0xC8).readPointer(), "ctx-cb");
                    var cfg = this.ssl.add(8).readPointer();
                    if (!cfg.isNull()) wrapCustomCb(cfg.add(0x30).readPointer(), "cfg-cb");
                } catch (e) {}
            }
        });
    } catch (e) { console.log("[cert] hs attach fail: " + e.message); }

    try {
        Interceptor.attach(b.base.add(0x49dac), {
            onEnter: function (args) {
                var cb = args[2];
                if (cb.isNull()) return;
                wrapCustomCb(cb, "custom");
            }
        });
        Interceptor.attach(b.base.add(0x49db8), {
            onEnter: function (args) {
                var cb = args[2];
                if (cb.isNull()) return;
                wrapCustomCb(cb, "custom-per-ssl");
            }
        });
    } catch (e) { console.log("[cert] reg attach fail: " + e.message); }

    // QUIC 降级
    try {
        var p = Module.findExportByName("libsscronet.so", "Cronet_EngineParams_enable_quic_set");
        if (p) {
            Interceptor.attach(p, { onEnter: function (args) { args[1] = ptr(0); } });
            console.log("[cert] QUIC 强制关闭 armed");
        }
    } catch (e) {}

    armed = true;
    console.log("[cert] FORGE(含图片域名) 武装完成");
}

armCert();
setInterval(armCert, 2000);

rpc.exports = {
    status: function () { return stats; }
};

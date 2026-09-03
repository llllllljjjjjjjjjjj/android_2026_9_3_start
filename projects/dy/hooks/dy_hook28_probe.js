// dy_hook28_probe.js v8 — 第二道证书校验现场
//
// v7 病因：custom_verify 回调放行后，握手仍失败，错误队列出现 lib=35 reason=202
//   （字节自定义错误库），sscronet 映射成 net_error=-202 = ERR_CERT_AUTHORITY_INVALID
//   → 存在"第二道证书校验"（疑似 tt 魔改版 X509_verify_cert，在 libttcrypto.so）
//
// 本版：
//   1) hook ERR_put_error（libttcrypto+0xb6594）：lib==35 时打印 reason/file/line + 调用链
//      → 抓到谁在往错误队列塞"未知 CA"
//   2) hook X509_verify_cert（libttcrypto+0xdab60）：打印校验结果 + X509_V_ERR 码
//      → 看第二道校验具体判的什么（自签/找不到签发者/不受信任）
//   3) 保留 v7 全部观测
//
// 用法：
//   adb forward tcp:27042 tcp:27042
//   .venv-frida-16.5.7\Scripts\frida.exe -H 127.0.0.1:27042 -f com.ss.android.ugc.aweme \
//       -l D:\reserve_agent\skills-portable-test\projects\dy\hooks\dy_hook28_probe.js

var FORGE = false;
var armed = false;

var API_RE = /amemv|qishui|snssdk|bytedance|douyin\.com|iesdouyin|zjcdn|byteimg|bytegoofy/;

var getServername = null;
var getSSLCTX = null;
var x509CtxGetError = null;   // int X509_STORE_CTX_get_error(X509_STORE_CTX*)
var wrapped = {};
var lastHost = "(none)";
var curHsHost = "(none)";
var stats = { hs: 0, hsFail: 0, cbCalls: 0, err35: 0, x509: 0, x509Fail: 0 };

var V_ERR_NAMES = {
    2: "UNABLE_TO_GET_ISSUER_CERT",
    18: "DEPTH_ZERO_SELF_SIGNED_CERT",
    19: "SELF_SIGNED_CERT_IN_CHAIN",
    20: "UNABLE_TO_GET_ISSUER_CERT_LOCALLY",
    21: "UNABLE_TO_VERIFY_LEAF_SIGNATURE",
    25: "PATH_LENGTH_EXCEEDED",
    26: "INVALID_PURPOSE",
    27: "CERT_UNTRUSTED",
    29: "SUBJECT_ISSUER_MISMATCH",
    42: "UNABLE_TO_VERIFY_LEAF_SIGNATURE",
    50: "APPLICATION_VERIFICATION",
    62: "HOSTNAME_MISMATCH"
};

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
    } catch (e) { return "(err)"; }
}

function whereIs(a) {
    var m = Process.findModuleByAddress(a);
    return m ? m.name + "+0x" + a.sub(m.base).toString(16) : String(a);
}

function wrapCustomCb(cb, tag) {
    if (cb.isNull() || wrapped[cb.toString()]) return;
    var m = Process.findModuleByAddress(cb);
    if (m && m.name === "libvcn.so") return;   // 视频路径，别动
    wrapped[cb.toString()] = true;
    try {
        console.log("[cb] wrap " + tag + " @ " + whereIs(cb));
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
                if (API_RE.test(h) || r === 0) {
                    console.log("[cb] " + tag + " host=" + h + " ret=" + r +
                                (r === 0 ? "  ←拒绝!" : ""));
                }
                if (FORGE && API_RE.test(h) && r === 0) {
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
    var c = Process.findModuleByName("libttcrypto.so");
    var s = Process.findModuleByName("libsscronet.so");
    if (!b || !c || !s) return;

    try {
        getServername = new NativeFunction(b.base.add(0x49d6c), 'pointer', ['pointer', 'int']);
        getSSLCTX = new NativeFunction(b.base.add(0x4a638), 'pointer', ['pointer']);
        x509CtxGetError = new NativeFunction(c.base.add(0xdbe78), 'int', ['pointer']);
    } catch (e) { console.log("[probe] natives init fail: " + e.message); return; }

    // ---- 1) ERR_put_error：抓 lib=35 的上报现场 ----
    try {
        Interceptor.attach(c.base.add(0xb6594), {
            onEnter: function (args) {
                this.lib = args[0].toInt32();
                this.reason = args[2].toInt32();
                this.file = args[3].isNull() ? "(null)" : args[3].readCString();
                this.line = args[4].toInt32();
            },
            onLeave: function (ret) {
                if (this.lib !== 35) return;
                stats.err35++;
                console.log("[puterr] lib=35 reason=" + this.reason +
                            " file=" + this.file + ":" + this.line +
                            "  BT: " + backtraceStr(this.context, 8));
            }
        });
        console.log("[probe] ERR_put_error armed @ " + c.base.add(0xb6594));
    } catch (e) { console.log("[probe] err_put attach fail: " + e.message); }

    // ---- 2) X509_verify_cert：第二道校验现场 ----
    try {
        Interceptor.attach(c.base.add(0xdab60), {
            onEnter: function (args) {
                this.ctx = args[0];
                this.host = curHsHost;
            },
            onLeave: function (ret) {
                stats.x509++;
                var r = ret.toInt32();
                var verr = -1;
                try { verr = x509CtxGetError(this.ctx); } catch (e) { }
                if (r === 0) stats.x509Fail++;
                if (API_RE.test(this.host) || r === 0) {
                    console.log("[x509] host=" + this.host + " ret=" + r +
                                " v_err=" + verr +
                                (V_ERR_NAMES[verr] ? " (" + V_ERR_NAMES[verr] + ")" : "") +
                                (r === 0 ? "  ←第二道校验拒绝!" : ""));
                }
            }
        });
        console.log("[probe] X509_verify_cert armed @ " + c.base.add(0xdab60));
    } catch (e) { console.log("[probe] x509 attach fail: " + e.message); }

    // ---- 3) SSL_get_error（记录 host 联动）----
    try {
        Interceptor.attach(b.base.add(0x4901c), {
            onEnter: function (args) {
                this.ssl = args[0];
                this.ret = args[1].toInt32();
                lastHost = hostOf(this.ssl);
                this.host = lastHost;
            },
            onLeave: function (ret) {
                var code = ret.toInt32();
                if (API_RE.test(this.host) || code === 16 || code === 13) {
                    console.log("[err] SSL_get_error host=" + this.host + " do_hs_ret=" + this.ret +
                                " ssl_error=" + code);
                }
            }
        });
    } catch (e) { }

    // ---- 4) 握手现场 ----
    try {
        Interceptor.attach(b.base.add(0x486c0), {
            onEnter: function (args) {
                this.ssl = args[0];
                this.host = hostOf(this.ssl);
                curHsHost = this.host;
                try {
                    var ctx = getSSLCTX(this.ssl);
                    if (!ctx.isNull()) wrapCustomCb(ctx.add(0xC8).readPointer(), "ctx-cb");
                    var cfg = this.ssl.add(8).readPointer();
                    if (!cfg.isNull()) wrapCustomCb(cfg.add(0x30).readPointer(), "cfg-cb");
                } catch (e) { }
            },
            onLeave: function (ret) {
                stats.hs++;
                var r = ret.toInt32();
                if (r <= 0) {
                    stats.hsFail++;
                    console.log("[hs] FAIL host=" + this.host + " ret=" + r);
                } else if (API_RE.test(this.host)) {
                    console.log("[hs] OK  host=" + this.host);
                }
            }
        });
    } catch (e) { }

    // ---- 5) 注册点 ----
    try {
        Interceptor.attach(b.base.add(0x49dac), {
            onEnter: function (args) {
                var cb = args[2];
                if (cb.isNull()) return;
                console.log("[reg] SSL_CTX_set_custom_verify ctx=" + args[0] + " mode=" + args[1] +
                            " cb=" + whereIs(cb) + "  BT: " + backtraceStr(this.context, 4));
                wrapCustomCb(cb, "custom");
            }
        });
        Interceptor.attach(b.base.add(0x49db8), {
            onEnter: function (args) {
                var cb = args[2];
                if (cb.isNull()) return;
                console.log("[reg] SSL_set_custom_verify ssl=" + args[0] + " mode=" + args[1] +
                            " cb=" + whereIs(cb) + "  host=" + hostOf(args[0]));
                wrapCustomCb(cb, "custom-per-ssl");
            }
        });
        Interceptor.attach(b.base.add(0x50810), {
            onEnter: function (args) {
                var cb = args[2];
                if (cb.isNull()) return;
                console.log("[reg] SSL_CTX_set_verify ctx=" + args[0] + " mode=" + args[1] +
                            " cb=" + whereIs(cb) + "  BT: " + backtraceStr(this.context, 4));
            }
        });
    } catch (e) { }

    armed = true;
    console.log("[probe] v8 全部武装完成 (FORGE=" + FORGE + ")");
}

// QUIC 降级
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
    } catch (e) { }
}

arm();
armQuic();
setInterval(function () { arm(); armQuic(); }, 2000);

setInterval(function () {
    if (armed) {
        console.log("[beat] 握手 " + stats.hs + " 次 / 失败 " + stats.hsFail +
                    " 次 / puterr35 " + stats.err35 + " 次 / x509 " + stats.x509 +
                    " 次(拒 " + stats.x509Fail + ") / 回调 " + stats.cbCalls + " 次 (FORGE=" + FORGE + ")");
    }
}, 30000);

rpc.exports = {
    forge: function (v) {
        FORGE = !!v;
        return "FORGE=" + FORGE + " (API 主机的 custom_verify 回调强制放行)";
    },
    status: function () {
        return { armed: armed, forge: FORGE, quic: quicArmed, stats: stats };
    }
};

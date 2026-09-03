// dy_hook29_probe.js v9 — 清队列绕过试验
//
// v8 结论：lib=35 reason=202（→net_error -202 CERT_AUTHORITY_INVALID）是 sscronet 自己合成的
//   记号错误（file=(null):-1，调用点 libsscronet+0x3dbffc）。X509_verify_cert 全程没被调用。
//   → 推断：门卫回调放行 amemv 的同时往 ERR 队列塞了记号错误，魔改 BoringSSL 握手看到队列
//     非空就中断。绕法：回调放行后立刻 ERR_clear_error() 清队列。
//
// 本版：
//   1) [自动清队列] custom_verify 回调对 API 主机返回后 → ERR_clear_error()（默认开启，可 RPC 关）
//   2) 观测升级：puterr 全库记录（SSL/X509/35）+ ERR_peek(来自SSL_get_error) + SSL_get_verify_result
//   3) 保留 v8 全部观测（握手现场/cb/x509/注册点/QUIC）
//
// 用法：
//   adb forward tcp:27042 tcp:27042
//   .venv-frida-16.5.7\Scripts\frida.exe -H 127.0.0.1:27042 -f com.ss.android.ugc.aweme \
//       -l D:\reserve_agent\skills-portable-test\projects\dy\hooks\dy_hook29_probe.js

var FORGE = false;
var AUTOCLEAR = true;   // ← 关键开关：回调放行后清空 ERR 队列
var armed = false;

var API_RE = /amemv|qishui|snssdk|bytedance|douyin\.com|iesdouyin|zjcdn|byteimg|bytegoofy/;

var getServername = null;
var getSSLCTX = null;
var x509CtxGetError = null;
var errClear = null;        // void ERR_clear_error()
var wrapped = {};
var lastHost = "(none)";
var curHsHost = "(none)";
var stats = { hs: 0, hsFail: 0, cbCalls: 0, cleared: 0, err35: 0, x509: 0, x509Fail: 0 };

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
                var isApi = API_RE.test(h);
                if (isApi || r === 0) {
                    console.log("[cb] " + tag + " host=" + h + " ret=" + r +
                                (r === 0 ? "  ←拒绝!" : ""));
                }
                if (isApi && r === 0 && FORGE) {
                    ret.replace(1);
                    try { if (this.alert && !this.alert.isNull()) this.alert.writeU8(0); } catch (e) {}
                    console.log("[cb] " + h + " 结果被 forge 为通过");
                }
                // ★ 清队列：门卫返回后清掉它（或握手过程）塞进队列的记号错误
                if (isApi && AUTOCLEAR && errClear) {
                    try {
                        errClear();
                        stats.cleared++;
                    } catch (e) { }
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
        errClear = new NativeFunction(c.base.add(0xb6014), 'void', []);
    } catch (e) { console.log("[probe] natives init fail: " + e.message); return; }

    // ---- 1) ERR_put_error：全库观测（SSL=16/X509=11/自定义=35）----
    try {
        Interceptor.attach(c.base.add(0xb6594), {
            onEnter: function (args) {
                this.lib = args[0].toInt32();
                this.reason = args[2].toInt32();
                this.file = args[3].isNull() ? "(null)" : args[3].readCString();
                this.line = args[4].toInt32();
            },
            onLeave: function (ret) {
                if (this.lib === 35) stats.err35++;
                if (this.lib === 35 || this.lib === 16 || this.lib === 11) {
                    console.log("[puterr] lib=" + this.lib + " reason=" + this.reason +
                                " file=" + this.file + ":" + this.line +
                                "  BT: " + backtraceStr(this.context, 8));
                }
            }
        });
        console.log("[probe] ERR_put_error armed");
    } catch (e) { }

    // ---- 2) ERR_peek_error：SSL_get_error 内部读到的队列顶 ----
    try {
        var sgeStart = b.base.add(0x4901c), sgeEnd = b.base.add(0x49134);
        Interceptor.attach(c.base.add(0xb5f8c), {
            onEnter: function (args) {
                this.ra = this.returnAddress;
                this.fromSGE = (this.ra.compare(sgeStart) >= 0 && this.ra.compare(sgeEnd) < 0);
            },
            onLeave: function (ret) {
                if (!this.fromSGE) return;
                var code = ret.toUInt32();
                if (code !== 0) {
                    console.log("[errq] " + lastHost + " queue-top=0x" + code.toString(16));
                }
            }
        });
        console.log("[probe] ERR_peek_error(来自SSL_get_error) armed");
    } catch (e) { }

    // ---- 3) X509_verify_cert ----
    try {
        Interceptor.attach(c.base.add(0xdab60), {
            onEnter: function (args) { this.ctx = args[0]; this.host = curHsHost; },
            onLeave: function (ret) {
                stats.x509++;
                var r = ret.toInt32();
                if (r === 0) stats.x509Fail++;
                var verr = -1;
                try { verr = x509CtxGetError(this.ctx); } catch (e) { }
                console.log("[x509] host=" + this.host + " ret=" + r + " v_err=" + verr);
            }
        });
        console.log("[probe] X509_verify_cert armed");
    } catch (e) { }

    // ---- 4) SSL_get_verify_result：握手后 BoringSSL 自己的判决 ----
    try {
        Interceptor.attach(b.base.add(0x50834), {
            onEnter: function (args) { this.host = hostOf(args[0]); },
            onLeave: function (ret) {
                if (API_RE.test(this.host)) {
                    console.log("[vr] host=" + this.host + " verify_result=" + ret.toInt32());
                }
            }
        });
        console.log("[probe] SSL_get_verify_result armed");
    } catch (e) { }

    // ---- 5) SSL_get_error ----
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

    // ---- 6) 握手现场 ----
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

    // ---- 7) 注册点 ----
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
    console.log("[probe] v9 全部武装完成 (FORGE=" + FORGE + ", AUTOCLEAR=" + AUTOCLEAR + ")");
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
        console.log("[beat] 握手 " + stats.hs + " 次/失败 " + stats.hsFail +
                    " / 回调 " + stats.cbCalls + " / 清队列 " + stats.cleared +
                    " / err35 " + stats.err35 + " / x509 " + stats.x509 +
                    "(拒" + stats.x509Fail + ") (FORGE=" + FORGE + " AUTOCLEAR=" + AUTOCLEAR + ")");
    }
}, 30000);

rpc.exports = {
    forge: function (v) {
        FORGE = !!v;
        return "FORGE=" + FORGE;
    },
    autoclear: function (v) {
        AUTOCLEAR = !!v;
        return "AUTOCLEAR=" + AUTOCLEAR + " (回调放行后清空 ERR 队列)";
    },
    status: function () {
        return { armed: armed, forge: FORGE, autoclear: AUTOCLEAR, quic: quicArmed, stats: stats };
    }
};

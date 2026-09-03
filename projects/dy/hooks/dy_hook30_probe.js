// dy_hook30_probe.js v10 — forge 方向修正版
//
// v9 结论 + IDA 反汇编（sub_38D0C = 魔改版证书校验）：
//   字节魔改 BoringSSL 的 custom_verify 回调语义反转：
//     返回 0 = 通过（走正常路径，清标记）
//     返回 1 = 拒绝（config+0xE8 验证模式位非零时 → 塞 lib16/125 handshake.cc:393 → 握手死）
//   而 sscronet 回调对 Charles 证书返回 1（拒绝）→ 这就是 amemv 一直失败的真正原因。
//   v9 的 forge（0→1）方向完全反了。
//
// 本版：FORGE=true 默认开启，回调对 API 主机返回 1 时强制改成 0（+alert 清零）。
//   保留 v9 全部观测（puterr/errq/x509/vr/握手现场/注册点/QUIC 降级）。
//
// 用法：
//   adb forward tcp:27042 tcp:27042
//   .venv-frida-16.5.7\Scripts\frida.exe -H 127.0.0.1:27042 -f com.ss.android.ugc.aweme \
//       -l D:\reserve_agent\skills-portable-test\projects\dy\hooks\dy_hook30_probe.js

var FORGE = true;     // ← 默认开启：回调返回 1(拒绝) → 改成 0(通过)
var AUTOCLEAR = true; // 回调放行后清空 ERR 队列（保留，双保险）
var armed = false;

var API_RE = /amemv|qishui|snssdk|bytedance|douyin\.com|iesdouyin|zjcdn|byteimg|bytegoofy/;

var getServername = null;
var getSSLCTX = null;
var x509CtxGetError = null;
var errClear = null;        // void ERR_clear_error()
var wrapped = {};
var lastHost = "(none)";
var curHsHost = "(none)";
var stats = { hs: 0, hsFail: 0, cbCalls: 0, forged: 0, cleared: 0, err35: 0, x509: 0, x509Fail: 0 };

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
                                (r === 0 ? "  ←通过" : ""));
                }
                // ★ v10 核心：API 主机回调返回 1(拒绝) → 改成 0(通过)
                if (isApi && r === 1 && FORGE) {
                    ret.replace(0);
                    try { if (this.alert && !this.alert.isNull()) this.alert.writeU8(0); } catch (e) {}
                    stats.forged++;
                    console.log("[cb] " + h + " 拒绝(1) 被 forge 为通过(0)");
                }
                // 清队列：门卫返回后清掉过程中塞的记号错误（保留 v9 的保险）
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
    console.log("[probe] v10 全部武装完成 (FORGE=" + FORGE + ", AUTOCLEAR=" + AUTOCLEAR + ")");
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
                    " / 回调 " + stats.cbCalls + " / forge " + stats.forged +
                    " / 清队列 " + stats.cleared + " / err35 " + stats.err35 +
                    " / x509 " + stats.x509 + "(拒" + stats.x509Fail + ")" +
                    " (FORGE=" + FORGE + " AUTOCLEAR=" + AUTOCLEAR + ")");
    }
}, 30000);

rpc.exports = {
    forge: function (v) {
        FORGE = !!v;
        return "FORGE=" + FORGE + " (回调拒绝 1 → 改通过 0)";
    },
    autoclear: function (v) {
        AUTOCLEAR = !!v;
        return "AUTOCLEAR=" + AUTOCLEAR + " (回调后清空 ERR 队列)";
    },
    status: function () {
        return { armed: armed, forge: FORGE, autoclear: AUTOCLEAR, quic: quicArmed, stats: stats };
    }
};

// dy_hook27_probe.js v7 — 握手失败精确病因
//
// v6 结论：隧道通、门卫放行、握手死在门卫之后的密码学阶段（ssl_error=1 = ERR 队列有真错误）。
//   NativeFunction 直调 ERR_error_string_n 失败 → 本版全部改用 Interceptor hook：
//   1) hook ERR_peek_error（libttcrypto.so+0xb5f8c）：SSL_get_error 内部会先调它，
//      从 returnAddress 判断调用来源，抓到失败时刻的原始错误码（库+原因码）
//   2) hook sscronet 的 sub_3DB8EC（ssl 错误码 → net_error 映射，libsscronet.so+0x3DB8EC）：
//      拿到 Chromium 风格的 net_error（-107=SSL_PROTOCOL_ERROR 之类）
//   3) 保留：握手现场、custom_verify 包装（跳过 libvcn）、注册点、QUIC 降级
//
// 用法：
//   adb forward tcp:27042 tcp:27042
//   .venv-frida-16.5.7\Scripts\frida.exe -H 127.0.0.1:27042 -f com.ss.android.ugc.aweme \
//       -l D:\reserve_agent\skills-portable-test\projects\dy\hooks\dy_hook27_probe.js

var FORGE = false;
var armed = false;

var API_RE = /amemv|qishui|snssdk|bytedance|douyin\.com|iesdouyin|zjcdn|byteimg|bytegoofy/;

var getServername = null;
var getSSLCTX = null;
var wrapped = {};
var lastHost = "(none)";
var stats = { hs: 0, hsFail: 0, cbCalls: 0, errq: 0, neterr: 0 };

// BoringSSL 常见 reason 码小表（lib=2 SSL / lib=4 X509 等）
var REASON_NAMES = {
    "2:0x86": "CERTIFICATE_VERIFY_FAILED",
    "2:0x95": "DIGEST_CHECK_FAILED",
    "2:0x84": "INVALID_MAC",
    "2:0x8f": "NO_SHARED_CIPHER",
    "2:0x412": "SSLV3_ALERT_BAD_CERTIFICATE",
    "2:0x418": "SSLV3_ALERT_HANDSHAKE_FAILURE",
    "2:0x428": "SSLV3_ALERT_ILLEGAL_PARAMETER",
    "2:0x43c": "SSLV3_ALERT_UNKNOWN_CA",
    "2:0x42e": "SSLV3_ALERT_CERTIFICATE_EXPIRED",
    "2:0x44a": "SSLV3_ALERT_CERTIFICATE_UNKNOWN",
    "2:0x436": "SSLV3_ALERT_PROTOCOL_VERSION",
    "2:0x450": "SSLV3_ALERT_BAD_RECORD_MAC",
    "2:0x7d": "BAD_HANDSHAKE_RECORD",
    "2:0x9d": "EXCESSIVE_MESSAGE_SIZE",
    "2:0x414": "SSLV3_ALERT_BAD_CERTIFICATE_STATUS",
    "2:0x411": "SSLV3_ALERT_DECOMPRESSION_FAILURE",
    "4:0x88": "X509_CERT_ALREADY_IN_HASH_TABLE",
    "4:0x7a": "X509_V_ERR_DEPTH_ZERO_SELF_SIGNED_CERT",
    "4:0x7c": "X509_V_ERR_SELF_SIGNED_CERT_IN_CHAIN",
};

function decodeErr(code) {
    var v = code.toUInt32();
    var lib = (v >>> 24) & 0xFF;
    var reason = (v >>> 12) & 0xFFF;
    var key = lib + ":0x" + reason.toString(16);
    var name = REASON_NAMES[key] || "?";
    return "lib=" + lib + " reason=0x" + reason.toString(16) + " (" + name + ")";
}

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
                if (FORGE && isApi && r === 0) {
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
    } catch (e) { console.log("[probe] natives init fail: " + e.message); return; }

    // ---- 1) SSL_get_error：记录 host，联动后续 hook ----
    var sgeStart = b.base.add(0x4901c), sgeEnd = b.base.add(0x49134);
    try {
        Interceptor.attach(sgeStart, {
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
                                " ssl_error=" + code +
                                (code === 16 ? " =WANT_CERTIFICATE_VERIFY!" : "") +
                                (code === 13 ? " =WANT_PRIVATE_KEY_OPERATION!" : ""));
                }
            }
        });
        console.log("[probe] SSL_get_error armed");
    } catch (e) { console.log("[probe] ssl_get_error attach fail: " + e.message); }

    // ---- 2) ERR_peek_error：抓原始错误码（只认来自 SSL_get_error 内部的调用）----
    try {
        Interceptor.attach(c.base.add(0xb5f8c), {
            onEnter: function (args) {
                this.ra = this.returnAddress;
                this.fromSGE = (this.ra.compare(sgeStart) >= 0 && this.ra.compare(sgeEnd) < 0);
            },
            onLeave: function (ret) {
                if (!this.fromSGE) return;
                stats.errq++;
                var code = ret.toUInt32();
                if (code !== 0) {
                    console.log("[errq] " + lastHost + " ERR=" + decodeErr(ret) +
                                " raw=0x" + code.toString(16));
                }
            }
        });
        console.log("[probe] ERR_peek_error armed @ " + c.base.add(0xb5f8c));
    } catch (e) { console.log("[probe] err_peek attach fail: " + e.message); }

    // ---- 3) sub_3DB8EC：ssl 错误码 → net_error 映射 ----
    try {
        Interceptor.attach(s.base.add(0x3DB8EC), {
            onEnter: function (args) {
                this.host = lastHost;
                this.sslErr = args[1].toInt32();
            },
            onLeave: function (ret) {
                stats.neterr++;
                console.log("[neterr] host=" + this.host + " ssl_error=" + this.sslErr +
                            " → net_error=" + ret.toInt32());
            }
        });
        console.log("[probe] sub_3DB8EC (ssl→net 映射) armed");
    } catch (e) { console.log("[probe] neterr attach fail: " + e.message); }

    // ---- 4) 握手现场 ----
    try {
        Interceptor.attach(b.base.add(0x486c0), {
            onEnter: function (args) {
                this.ssl = args[0];
                this.host = hostOf(this.ssl);
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
                var h = this.host;
                if (r <= 0) {
                    stats.hsFail++;
                    console.log("[hs] FAIL host=" + h + " ret=" + r);
                } else if (API_RE.test(h)) {
                    console.log("[hs] OK  host=" + h);
                }
            }
        });
        console.log("[probe] SSL_do_handshake 握手现场 armed");
    } catch (e) { console.log("[probe] handshake attach fail: " + e.message); }

    // ---- 5) 注册点（3 参数）----
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
        console.log("[probe] verify 注册点 armed");
    } catch (e) { console.log("[probe] reg attach fail: " + e.message); }

    armed = true;
    console.log("[probe] v7 全部武装完成 (FORGE=" + FORGE + ")");
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
    } catch (e) { console.log("[quic] attach fail: " + e.message); }
}

arm();
armQuic();
setInterval(function () { arm(); armQuic(); }, 2000);

setInterval(function () {
    if (armed) {
        console.log("[beat] 握手 " + stats.hs + " 次 / 失败 " + stats.hsFail +
                    " 次 / errq " + stats.errq + " 次 / neterr " + stats.neterr +
                    " 次 / 回调 " + stats.cbCalls + " 次 (FORGE=" + FORGE + ")");
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

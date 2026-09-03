// dy_hook25_probe.js v5 — 握手现场探针（libttboringssl.so）
//
// v4 教训：字节的 BoringSSL 里 SSL_CTX_set_custom_verify(ctx, mode, cb) 是 3 参数，
//   回调在 args[2]（mode=1 被误当成了回调）。而且评论 API 的上下文可能早于 frida 建立，
//   注册点蹲不到 → 本版直接蹲 SSL_do_handshake：每个 TLS 握手都经过这里。
//
// 原理：
//   SSL_CTX_set_custom_verify: 回调存 [ctx+0xC8]
//   SSL_set_custom_verify:     回调存 [[ssl+8]+0x30]（config）
//   SSL_get_SSL_CTX(ssl) → ctx；SSL_get_verify_result(ssl) → 判决原因码
//   原因码 50 = X509_V_ERR_APPLICATION_VERIFICATION = custom verify 回调返回 0（pin 拒绝）
//
// 行为：
//   1) 每个握手 onEnter：读 ssl→ctx→[0xC8] 和 ssl→config→[0x30] 的回调并包装（无论何时注册）
//   2) 每个握手 onLeave：API 主机或失败 → 打印 host/ret/verify_result；失败打调用链
//   3) forge(true)：被包装的回调对 API 主机强制返回 1（放行）
//
// 用法：
//   adb forward tcp:27042 tcp:27042
//   .venv-frida-16.5.7\Scripts\frida.exe -H 127.0.0.1:27042 -f com.ss.android.ugc.aweme \
//       -l D:\reserve_agent\skills-portable-test\projects\dy\hooks\dy_hook25_probe.js

var FORGE = false;
var armed = false;

var API_RE = /amemv|qishui|snssdk|bytedance|douyin\.com|iesdouyin|zjcdn|byteimg|bytegoofy/;

var getServername = null;   // const char* SSL_get_servername(SSL*, int)
var getSSLCTX = null;       // SSL_CTX* SSL_get_SSL_CTX(SSL*)
var getVerifyResult = null; // long SSL_get_verify_result(SSL*)
var wrapped = {};           // 已包装回调地址去重
var stats = { hs: 0, hsFail: 0, cbCalls: 0, vr50: 0 };

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

// 包装 custom_verify 回调：int (*)(SSL*, uint8_t* out_alert)
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
                var isApi = API_RE.test(h);
                if (isApi || r === 0) {
                    console.log("[cb] " + tag + " host=" + h + " ret=" + r +
                                (r === 0 ? "  ←拒绝!" : ""));
                    if (isApi && r === 0) {
                        console.log("[cb] 拒绝现场 BT: " + backtraceStr(this.context, 8));
                    }
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
    if (!b) return;

    try {
        getServername = new NativeFunction(b.base.add(0x49d6c), 'pointer', ['pointer', 'int']);
        getSSLCTX = new NativeFunction(b.base.add(0x4a638), 'pointer', ['pointer']);
        getVerifyResult = new NativeFunction(b.base.add(0x50834), 'long', ['pointer']);
    } catch (e) { console.log("[probe] natives init fail: " + e.message); return; }

    // ---- 握手现场 ----
    try {
        Interceptor.attach(b.base.add(0x486c0), {   // SSL_do_handshake
            onEnter: function (args) {
                this.ssl = args[0];
                this.host = hostOf(this.ssl);
                // 不管上下文何时注册，握手前现挖回调并包装
                try {
                    var ctx = getSSLCTX(this.ssl);
                    if (!ctx.isNull()) {
                        wrapCustomCb(ctx.add(0xC8).readPointer(), "ctx-cb");
                    }
                    var cfg = this.ssl.add(8).readPointer();
                    if (!cfg.isNull()) {
                        wrapCustomCb(cfg.add(0x30).readPointer(), "cfg-cb");
                    }
                } catch (e) { }
            },
            onLeave: function (ret) {
                stats.hs++;
                var r = ret.toInt32();
                var h = this.host;
                var isApi = API_RE.test(h);
                if (r <= 0) {
                    stats.hsFail++;
                    var vr = -1;
                    try { vr = getVerifyResult(this.ssl).toInt32(); } catch (e) { }
                    if (vr === 50) stats.vr50++;
                    console.log("[hs] FAIL host=" + h + " ret=" + r + " verify_result=" + vr +
                                (vr === 50 ? "  ←custom_verify 回调拒绝(pin)!" : ""));
                    if (isApi) {
                        console.log("[hs] 调用链 BT: " + backtraceStr(this.context, 8));
                    }
                } else if (isApi) {
                    console.log("[hs] OK  host=" + h);
                }
            }
        });
        console.log("[probe] SSL_do_handshake 握手现场 armed @ " + b.base.add(0x486c0));
    } catch (e) { console.log("[probe] handshake attach fail: " + e.message); }

    // ---- 注册点（3 参数！cb=args[2]）----
    try {
        Interceptor.attach(b.base.add(0x49dac), {   // SSL_CTX_set_custom_verify(ctx, mode, cb)
            onEnter: function (args) {
                var cb = args[2];
                if (cb.isNull()) return;
                console.log("[reg] SSL_CTX_set_custom_verify ctx=" + args[0] + " mode=" + args[1] +
                            " cb=" + whereIs(cb) + "  BT: " + backtraceStr(this.context, 4));
                wrapCustomCb(cb, "custom");
            }
        });
        Interceptor.attach(b.base.add(0x49db8), {   // SSL_set_custom_verify(ssl, mode, cb)
            onEnter: function (args) {
                var cb = args[2];
                if (cb.isNull()) return;
                console.log("[reg] SSL_set_custom_verify ssl=" + args[0] + " mode=" + args[1] +
                            " cb=" + whereIs(cb) + "  host=" + hostOf(args[0]));
                wrapCustomCb(cb, "custom-per-ssl");
            }
        });
        Interceptor.attach(b.base.add(0x50810), {   // SSL_CTX_set_verify(ctx, mode, cb)
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
    console.log("[probe] v5 全部武装完成 (FORGE=" + FORGE + ")");
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
                    " 次 / vr=50 " + stats.vr50 + " 次 / 回调执行 " + stats.cbCalls +
                    " 次 (FORGE=" + FORGE + ")");
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

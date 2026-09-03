// dy_hook26_probe.js v6 — 握手失败病因探针
//
// v5 结论：custom_verify 回调对 amemv.com 返回 1（放行），握手仍然失败 → pin 不是凶手。
//   需要 BoringSSL 错误队列的真实错误。
//   字节魔改的 sscronet 把 SSL_get_error 的 16(WANT_CERTIFICATE_VERIFY) / 13(WANT_PRIVATE_KEY)
//   当致命错误直接放弃握手（sub_3DA454: CMP W0,#0x10 B.EQ fail）。
//
// 本版新增：
//   hook SSL_get_error(ssl, ret)：API 主机或错误码∈{13,16} → 打印 主机/错误码/ERR 队列字符串
//   通过 ERR_peek_error + ERR_error_string_n（libttcrypto.so）直接读出人类可读病因
//
// 行为保留：
//   握手现场 SSL_do_handshake 观测 + custom_verify 回调包装（跳过 libvcn.so 的视频回调，
//   排除 v5 视频异常的嫌疑）+ verify 注册点 + QUIC 降级 + forge 后门
//
// 用法：
//   adb forward tcp:27042 tcp:27042
//   .venv-frida-16.5.7\Scripts\frida.exe -H 127.0.0.1:27042 -f com.ss.android.ugc.aweme \
//       -l D:\reserve_agent\skills-portable-test\projects\dy\hooks\dy_hook26_probe.js

var FORGE = false;
var armed = false;

var API_RE = /amemv|qishui|snssdk|bytedance|douyin\.com|iesdouyin|zjcdn|byteimg|bytegoofy/;

var getServername = null;
var getSSLCTX = null;
var errPeek = null;      // unsigned long ERR_peek_error()
var errStr = null;       // char* ERR_error_string_n(unsigned long, char*, size_t)
var wrapped = {};
var stats = { hs: 0, hsFail: 0, cbCalls: 0, err16: 0, err13: 0 };

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

// 读取 ERR 队列的当前错误并转成字符串
function errQueueString() {
    try {
        if (!errPeek || !errStr) return "(no err fns)";
        var e = errPeek();
        if (e.toUInt32() === 0) return "(err queue empty)";
        var buf = Memory.alloc(256);
        errStr(e, buf, 256);
        return buf.readCString() + " [0x" + e.toString(16) + "]";
    } catch (ex) { return "(err read fail)"; }
}

// 包装 custom_verify 回调（跳过 libvcn.so 视频网络回调）
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
    if (!b || !c) return;

    try {
        getServername = new NativeFunction(b.base.add(0x49d6c), 'pointer', ['pointer', 'int']);
        getSSLCTX = new NativeFunction(b.base.add(0x4a638), 'pointer', ['pointer']);
        errPeek = new NativeFunction(c.base.add(0xb5f8c), 'uint64', []);
        errStr = new NativeFunction(c.base.add(0xb62f8), 'pointer', ['uint64', 'pointer', 'uint64']);
    } catch (e) { console.log("[probe] natives init fail: " + e.message); return; }

    // ---- 新增：SSL_get_error 病因捕获 ----
    try {
        Interceptor.attach(b.base.add(0x4901c), {
            onEnter: function (args) {
                this.ssl = args[0];
                this.ret = args[1].toInt32();
                this.host = hostOf(this.ssl);
            },
            onLeave: function (ret) {
                var code = ret.toInt32();
                var h = this.host;
                var isApi = API_RE.test(h);
                if (code === 16) stats.err16++;
                if (code === 13) stats.err13++;
                if (isApi || code === 16 || code === 13) {
                    console.log("[err] SSL_get_error host=" + h + " do_hs_ret=" + this.ret +
                                " ssl_error=" + code +
                                (code === 16 ? " =WANT_CERTIFICATE_VERIFY!" : "") +
                                (code === 13 ? " =WANT_PRIVATE_KEY_OPERATION!" : "") +
                                "  ERR: " + errQueueString());
                }
            }
        });
        console.log("[probe] SSL_get_error armed @ " + b.base.add(0x4901c));
    } catch (e) { console.log("[probe] ssl_get_error attach fail: " + e.message); }

    // ---- 握手现场 ----
    try {
        Interceptor.attach(b.base.add(0x486c0), {   // SSL_do_handshake
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
                var isApi = API_RE.test(h);
                if (r <= 0) {
                    stats.hsFail++;
                    console.log("[hs] FAIL host=" + h + " ret=" + r);
                } else if (isApi) {
                    console.log("[hs] OK  host=" + h);
                }
            }
        });
        console.log("[probe] SSL_do_handshake 握手现场 armed");
    } catch (e) { console.log("[probe] handshake attach fail: " + e.message); }

    // ---- 注册点（3 参数）----
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
    console.log("[probe] v6 全部武装完成 (FORGE=" + FORGE + ")");
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
                    " 次 / err16 " + stats.err16 + " 次 / err13 " + stats.err13 +
                    " 次 / 回调执行 " + stats.cbCalls + " 次 (FORGE=" + FORGE + ")");
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

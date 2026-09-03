// dy_hook23_probe.js v2 — native 证书校验探针（libsscronet.so / 抖音 38.0.0）
//
// 观测 libsscronet.so+0x27EC40（Cronet_CertVerify_DoVerifyV2 真实实现）：
//   int verify(CertVerify* obj, VerifyParamsV2* params, byte* out_knownRoot)
//   params: host@0, port@0x18, certs@0x20, flags@0x68, engine@0x70
//
// v2 改进：
//   - host 解析兼容多种字符串布局（堆指针 / 内联字符缓冲 / SSO）
//   - 打印调用链（backtrace），分辨 QUIC 握手 vs HTTPS 握手
//   - amemv/qishui/snssdk 等 API 域名无条件打印调用链
//
// RPC: forge(true) 伪造校验结果全通过 / mock(true) 新引擎注入 mock / status()
//
// 用法：
//   adb forward tcp:27042 tcp:27042
//   .venv-frida-16.5.7\Scripts\frida.exe -H 127.0.0.1:27042 -f com.ss.android.ugc.aweme \
//       -l D:\reserve_agent\skills-portable-test\projects\dy\hooks\dy_hook23_probe.js

var FORGE = false;
var MOCK = false;
var armed = false;

var trampolineFns = {}; // 蹦床 fn 去重
var counter = { total: 0, nonzero: 0 };

function readHost(p) {
    // 布局1: 前 8 字节是指针且指向已映射内存 → 堆字符串
    try {
        var cand = p.readPointer();
        if (!cand.isNull() && Process.findRangeByAddress(cand) !== null) {
            var s = cand.readCString();
            return s ? s : "(empty)";
        }
    } catch (e) { /* fallthrough */ }
    // 布局2: 内联字符缓冲（chars 直接存 p）
    try {
        var s2 = p.readCString();
        return s2 ? s2 : "(empty)";
    } catch (e2) { return "(unreadable)"; }
}

function backtraceStr(ctx) {
    try {
        var bt = Thread.backtrace(ctx, Backtracer.ACCURATE);
        var parts = [];
        for (var i = 0; i < bt.length && i < 5; i++) {
            var a = bt[i];
            var m = Process.findModuleByAddress(a);
            if (m) parts.push(m.name + "+0x" + a.sub(m.base).toString(16));
            else parts.push(a.toString());
        }
        return parts.join(" <- ");
    } catch (e) { return "(bt err)"; }
}

function arm() {
    if (armed) return;
    var m = Process.findModuleByName("libsscronet.so");
    if (!m) return;
    var base = m.base;
    console.log("[probe] libsscronet base=" + base);

    // ---- 观测 1：校验决策点 ----
    try {
        Interceptor.attach(base.add(0x27EC40), {
            onEnter: function (args) {
                try {
                    var params = args[1];
                    this.host = readHost(params);
                    this.port = params.add(0x18).readU16();
                    this.flags = params.add(0x68).readU32();
                    this.out = args[2];
                    var cbeg = params.add(0x20).readPointer();
                    var cend = params.add(0x28).readPointer();
                    var eng = params.add(0x70).readPointer();
                    this.api = /amemv|qishui|snssdk|bytedance|douyin\.com|iesdouyin|zjcdn|byteimg|bytegoofy/.test(this.host);
                    if (this.api) {
                        console.log("[verify] ENTER host=" + this.host + " port=" + this.port +
                                    " flags=" + this.flags + " certs=" + cbeg + "/" + cend +
                                    " engine=" + eng + "  BT: " + backtraceStr(this.context));
                    }
                } catch (e) {
                    console.log("[verify] ENTER parse err " + e.message);
                }
            },
            onLeave: function (ret) {
                try {
                    var st = ret.toInt32();
                    counter.total++;
                    var kr = this.out ? this.out.readU8() : -1;
                    if (this.api || st !== 0) {
                        counter.nonzero++;
                        console.log("[verify] LEAVE " + this.host + " status=" + st + " knownRoot=" + kr +
                                    (FORGE ? "  →FORGED" : ""));
                    }
                    if (FORGE) {
                        ret.replace(0);
                        if (this.out) this.out.writeU8(1);
                    }
                } catch (e) { console.log("[verify] LEAVE err " + e.message); }
            }
        });
        console.log("[probe] verify 决策点 sub_27EC40 armed @ " + base.add(0x27EC40));
    } catch (e) { console.log("[probe] verify attach fail: " + e.message); }

    // ---- 观测 2：引擎创建（MOCK 开启时注入全通过 mock 校验器）----
    var mockCb = null;
    if (MOCK) {
        mockCb = new NativeCallback(function (obj, params, out) {
            try {
                var host = params.isNull() ? "?" : readHost(params);
                console.log("[mock] VERIFY CALLED host=" + host + " → 返回通过");
                if (!out.isNull()) out.writeU8(1);
                return 0;
            } catch (e) {
                console.log("[mock] err " + e.message);
                return 0;
            }
        }, 'int', ['pointer', 'pointer', 'pointer']);
    }
    function onEngineCreated(engine, tag) {
        try {
            console.log("[eng] " + tag + " engine=" + engine +
                        " f238=" + engine.add(0x238).readPointer() +
                        " mock540=" + engine.add(0x540).readPointer());
            if (MOCK && engine.add(0x238).readPointer().isNull() && engine.add(0x540).readPointer().isNull()) {
                var mock = Memory.alloc(0x20);
                mock.add(0).writePointer(base.add(0x5D5B58));
                mock.add(8).writePointer(ptr(0));
                mock.add(0x10).writePointer(mockCb);
                mock.add(0x18).writePointer(ptr(0));
                var setMock = new NativeFunction(base.add(0x26ff98), 'void', ['pointer', 'pointer']);
                setMock(engine, mock);
                console.log("[mock] 已注入 mock 校验器 → engine+0x540");
            }
        } catch (e) { console.log("[eng] err " + e.message); }
    }
    try {
        Interceptor.attach(base.add(0x26ff64), { onLeave: function (r) { onEngineCreated(r, "Create"); } });
        Interceptor.attach(base.add(0x2774c0), { onLeave: function (r) { onEngineCreated(r, "CreateWith"); } });
        console.log("[probe] Cronet_Engine_Create/CreateWith armed (MOCK=" + MOCK + ")");
    } catch (e) { console.log("[probe] eng attach fail: " + e.message); }

    // ---- 观测 3：App 是否自行装 mock ----
    try {
        Interceptor.attach(base.add(0x26ff98), {
            onEnter: function (args) {
                console.log("[eng] SetMockCertVerifierForTesting(" + args[0] + ", " + args[1] + ")  ← App 自己在装 mock!");
            }
        });
    } catch (e) { }

    // ---- 观测 4：App 是否添加公钥 pin ----
    try {
        Interceptor.attach(base.add(0x2796e0), {
            onEnter: function (args) {
                try {
                    var pin = args[1];
                    console.log("[pins] public_key_pins_add! pin=" + pin +
                                " dump: " + hexdump(pin, { length: 0x40, ansi: false }).replace(/\n/g, " | "));
                } catch (e) { console.log("[pins] dump err " + e.message); }
            }
        });
        console.log("[probe] public_key_pins_add armed");
    } catch (e) { console.log("[probe] pins attach fail: " + e.message); }

    // ---- 观测 5：通用 fn-slot 蹦床（Executor/CertVerify 共享；只记 fn 偏移去重）----
    try {
        Interceptor.attach(base.add(0x2771d4), {
            onEnter: function (args) {
                try {
                    var fn = args[0].add(0x10).readPointer();
                    if (!fn.isNull() && fn >= base && fn < base.add(m.size)) {
                        var off = "0x" + fn.sub(base).toString(16);
                        if (!trampolineFns[off]) {
                            trampolineFns[off] = true;
                            console.log("[tramp] fn → libsscronet+" + off);
                        }
                    }
                } catch (e) { }
            }
        });
    } catch (e) { }

    armed = true;
}

// ---- QUIC 降级 ----
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

var lastBeat = 0;
setInterval(function () {
    if (armed) {
        console.log("[beat] 累计 verify " + counter.total + " 次 / 非零 status " + counter.nonzero + " 次");
    }
}, 30000);

rpc.exports = {
    forge: function (v) {
        FORGE = !!v;
        return "FORGE=" + FORGE + " (verify 决策点结果伪造为通过)";
    },
    mock: function (v) {
        MOCK = !!v;
        return "MOCK=" + MOCK + " (仅对之后新建的引擎生效，需重启 App)";
    },
    status: function () {
        return { armed: armed, forge: FORGE, mock: MOCK, quic: quicArmed };
    }
};

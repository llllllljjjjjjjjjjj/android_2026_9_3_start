// dy_hook47_stub_probe.js — 抓 x-ss-stub 生成输入 (0x26d248) 与输出
// 0x26d248(X0=?, X1=目标对象, X2=MD5输入ptr, X3=输入长度) → MD5 → hex → "x-ss-stub"
// 同时 hook 0x37ed64 SetHeader 捕获最终写入的 x-ss-stub 值
var sscronet = null;
var stubLog = [];

function hexDump(ptr, len) {
    try {
        var out = [];
        var cap = Math.min(len, 256);
        for (var i = 0; i < cap; i++) out.push(ptr.add(i).readU8().toString(16).padStart(2, "0"));
        return out.join("");
    } catch (e) { return "(read fail)"; }
}

function arm() {
    sscronet = Process.findModuleByName("libsscronet.so");
    if (!sscronet) return;
    try {
        Interceptor.attach(sscronet.base.add(0x26d248), {
            onEnter: function (args) {
                var x2 = args[2];
                var x3 = args[3].toInt32();
                this.x2 = x2;
                this.x3 = x3;
                try {
                    if (x3 > 0 && x3 < 4096) {
                        console.log("[stub-in] len=" + x3 + " hex=" + hexDump(x2, x3));
                        console.log("[stub-in] ascii=" + JSON.stringify(x2.readUtf8String(x3).replace(/[^\x20-\x7e]/g, ".")));
                    } else {
                        console.log("[stub-in] len=" + x3 + " (ptr=" + x2 + ")");
                    }
                } catch (e) { console.log("[stub-in] err: " + e); }
            }
        });
        console.log("[probe] 0x26d248 armed");
    } catch (e) { console.log("[probe] 26d248 attach fail: " + e.message); }

    // SetHeader 抓 x-ss-stub 写入
    try {
        Interceptor.attach(sscronet.base.add(0x37ed64), {
            onEnter: function (args) {
                try {
                    var kp = args[1].readPointer();
                    var kl = args[1].add(8).readS64();
                    var key = (kl > 0 && kl < 100) ? kp.readUtf8String(kl) : null;
                    if (key === "x-ss-stub") {
                        var vp = args[2].readPointer();
                        var vl = args[2].add(8).readS64();
                        var val = (vl > 0 && vl < 256) ? vp.readUtf8String(vl) : "?";
                        var ts = Date.now();
                        stubLog.push({ ts: ts, v: val });
                        if (stubLog.length > 50) stubLog.shift();
                        console.log("[stub-out] x-ss-stub => " + val);
                    }
                } catch (e) {}
            }
        });
        console.log("[probe] SetHeader armed");
    } catch (e) { console.log("[probe] sethdr attach fail: " + e.message); }
}

arm();
setInterval(arm, 3000);

rpc.exports = {
    laststub: function () {
        return stubLog.length ? stubLog[stubLog.length - 1] : null;
    },
    stubs: function () { return stubLog; }
};
console.log("[probe] stub probe loaded");

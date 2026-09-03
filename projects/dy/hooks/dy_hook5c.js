// 诊断版: timer 是否执行 + attach 是否抛异常
var ticks = 0;
var timer = setInterval(function () {
    ticks++;
    var base = Module.findBaseAddress("libsscronet.so");
    if (ticks % 100 === 1) console.log("[diag] tick=" + ticks + " sscronet=" + base);
    if (!base) return;
    clearInterval(timer);
    try {
        Interceptor.attach(base.add(0x37ed64), {
            onEnter: function (args) {
                try {
                    var kp = args[1].readPointer();
                    var kl = args[1].add(8).readS64();
                    var key = (kl > 0 && kl < 100) ? kp.readUtf8String(kl) : null;
                    if (key && (key.indexOf("x-") === 0 || key.indexOf("argus") >= 0 || key.indexOf("gorgon") >= 0)) {
                        var vp = args[2].readPointer();
                        var vl = args[2].add(8).readS64();
                        var val = (vl > 0 && vl < 4096) ? vp.readUtf8String(vl) : "?";
                        console.log("[SETHDR] " + key + " => " + val.substring(0, 600));
                    }
                } catch (e) { console.log("[SETHDR] inner err: " + e); }
            }
        });
        console.log("[diag] attached OK");
    } catch (e) {
        console.log("[diag] attach FAIL: " + e);
    }
}, 150);
console.log("[dy_hook5c] loaded");

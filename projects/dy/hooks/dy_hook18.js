// 抖音 38.0.0 八神抓取 v18 (frida 16.5.7, ES5, attach 模式)
// 诊断: SET-GOD 值的调用链 + metasec 回调 I/O 的 hexdump
//   1) 37ED64 onEnter: 八神 name → hexdump value + backtrace 6 帧模块化
//   2) metasec 28065c: args[0]/args[1] hexdump 48B + retval hexdump 64B
//   3) 47aafc: X21 hexdump (回调返回值)

function hexdump(p, n) {
    try {
        var b = p.readByteArray(n);
        return Array.prototype.map.call(new Uint8Array(b), function (x) { return ("0" + x.toString(16)).slice(-2); }).join("");
    } catch (e) { return "ERR:" + e; }
}

function readStdString(p) {
    try {
        var flag = p.add(0x17).readU8();
        if ((flag & 0x80) === 0) {
            if (flag > 0 && flag < 23) {
                var s = p.readUtf8String(flag);
                var ok = true;
                for (var i = 0; i < s.length; i++) { var c = s.charCodeAt(i); if (c < 0x20 || c > 0x7e) { ok = false; break; } }
                return ok ? s : null;
            }
            return null;
        }
        var ptr = p.readPointer();
        var len = p.add(8).readS64();
        if (len > 0 && len < 4096) {
            var s = ptr.readUtf8String(len);
            var ok = true;
            for (var i = 0; i < s.length; i++) { var c = s.charCodeAt(i); if (c < 0x20 || c > 0x7e) { ok = false; break; } }
            return ok ? s : null;
        }
    } catch (e) { }
    return null;
}

function tryRead(p) {
    // 多种方式读字符串: char* utf8 / std::string 对象
    if (p.isNull()) return null;
    var r = readStdString(p);
    if (r) return r;
    try {
        var s = p.readUtf8String(512);
        if (s && s.length > 0 && s.length < 512) return s;
    } catch (e) { }
    try {
        var q = p.readPointer();
        if (!q.isNull()) {
            var s2 = q.readUtf8String(512);
            if (s2 && s2.length > 0 && s2.length < 512) return s2;
        }
    } catch (e) { }
    return null;
}

function isGod(name) {
    var n = name.toLowerCase();
    var GOD = ["x-argus", "x-gorgon", "x-ladon", "x-khronos", "x-helios",
               "x-medusa", "x-soter", "x-perseus", "x-tython", "x-bogus", "x-ss-stub"];
    for (var i = 0; i < GOD.length; i++) if (n.indexOf(GOD[i]) === 0) return true;
    return false;
}

function bt(tag, n) {
    try {
        var bt = Thread.backtrace(this.context, Backtracer.ACCURATE);
        var out = [];
        for (var i = 0; i < Math.min(bt.length, n); i++) {
            var m = Process.findModuleByAddress(bt[i]);
            out.push(m ? m.name + "+" + bt[i].sub(m.base).toString(16) : String(bt[i]));
        }
        console.log(tag + " " + out.join(" <- "));
    } catch (e) { console.log(tag + " bt ERR " + e); }
}

var sbase = Module.findBaseAddress("libsscronet.so");
var mbase = Module.findBaseAddress("libmetasec_ml.so");
console.log("[base] sscronet=" + sbase + " metasec=" + mbase);

var cnt = { m: 0, blr2: 0, shgod: 0, bt: 0 };

// 1) SetHeader: 八神 name → hexdump value + backtrace (前 8 组)
try {
    Interceptor.attach(sbase.add(0x37ed64), {
        onEnter: function (args) {
            var name = readStdString(args[1]);
            if (name && isGod(name)) {
                cnt.shgod++;
                var val = tryRead(args[2]);
                var hex = hexdump(args[2], 48);
                console.log("[SET-GOD] #" + cnt.shgod + " " + name +
                    " val=" + (val ? val.substring(0, 120) : "?") +
                    " objhex=" + hex.substring(0, 96));
                if (cnt.bt < 8) {
                    cnt.bt++;
                    bt.call(this, "[SET-BT] #" + cnt.bt, 7);
                }
            }
        }
    });
    console.log("[37ed64] hooked");
} catch (e) { console.log("[37ed64] fail: " + e); }

// 2) metasec 回调: hexdump 入参出参 (前 8 次)
if (mbase) {
    try {
        Interceptor.attach(mbase.add(0x28065c), {
            onEnter: function (args) {
                cnt.m++;
                if (cnt.m <= 8) {
                    console.log("[MSEC-IN] #" + cnt.m +
                        " X0h=" + hexdump(args[0], 48).substring(0, 96) +
                        " X0s=" + (tryRead(args[0]) ? tryRead(args[0]).substring(0, 80) : "?") +
                        " X1h=" + hexdump(args[1], 48).substring(0, 96) +
                        " X1s=" + (tryRead(args[1]) ? tryRead(args[1]).substring(0, 80) : "?"));
                }
            },
            onLeave: function (retval) {
                if (cnt.m <= 8) {
                    console.log("[MSEC-OUT] #" + cnt.m +
                        " reth=" + hexdump(retval, 64).substring(0, 128) +
                        " rets=" + (tryRead(retval) ? tryRead(retval).substring(0, 200) : "?"));
                }
            }
        });
        console.log("[metasec 28065c] hooked");
    } catch (e) { console.log("[metasec 28065c] fail: " + e); }
}

// 3) 47aafc: BLR 返回值 X21 hexdump (前 8 次)
try {
    Interceptor.attach(sbase.add(0x47aafc), {
        onEnter: function (args) {
            cnt.blr2++;
            if (cnt.blr2 <= 8) {
                console.log("[BLR-RET] #" + cnt.blr2 +
                    " X21h=" + hexdump(this.context.x21, 64).substring(0, 128) +
                    " X21s=" + (tryRead(this.context.x21) ? tryRead(this.context.x21).substring(0, 200) : "?"));
            }
        }
    });
    console.log("[47aafc] hooked");
} catch (e) { console.log("[47aafc] fail: " + e); }

// 4) 心跳
setInterval(function () {
    console.log("[beat] m=" + cnt.m + " blr2=" + cnt.blr2 + " shgod=" + cnt.shgod + " bt=" + cnt.bt);
}, 15000);

console.log("[dy_hook18] loaded");

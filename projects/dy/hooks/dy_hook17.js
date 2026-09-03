// 抖音 38.0.0 八神抓取 v17 (frida 16.5.7, ES5, attach 模式)
// 目标: 抓 metasec 回调 (libmetasec_ml.so+0x28065c) 的入参出参明文
//   1) 直接 attach metasec 回调入口
//   2) 后备: 47aae4 (BLR 前, 读 X21/X22) + 47aafc (BLR 后, 读 X21=返回值)
//   3) SetHeader 过滤 + 心跳

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

function readMaybeStr(p) {
    if (p.isNull()) return null;
    try {
        var s = p.readUtf8String(512);
        if (s && s.length > 0 && s.length < 512) return s;
    } catch (e) { }
    return readStdString(p);
}

function isGod(name) {
    var n = name.toLowerCase();
    var GOD = ["x-argus", "x-gorgon", "x-ladon", "x-khronos", "x-helios",
               "x-medusa", "x-soter", "x-perseus", "x-tython", "x-bogus", "x-ss-stub"];
    for (var i = 0; i < GOD.length; i++) if (n.indexOf(GOD[i]) === 0) return true;
    return false;
}

var sbase = Module.findBaseAddress("libsscronet.so");
var mbase = Module.findBaseAddress("libmetasec_ml.so");
console.log("[base] sscronet=" + sbase + " metasec=" + mbase);

var cnt = { m: 0, blr: 0, blr2: 0, shgod: 0 };

// 1) 直接 hook metasec 回调入口
if (mbase) {
    try {
        Interceptor.attach(mbase.add(0x28065c), {
            onEnter: function (args) {
                cnt.m++;
                if (cnt.m <= 12) {
                    var a = readMaybeStr(args[0]);
                    var b = readMaybeStr(args[1]);
                    console.log("[MSEC-IN] #" + cnt.m +
                        " X0=" + (a ? a.substring(0, 200) : "?") +
                        " X1=" + (b ? b.substring(0, 300) : "?"));
                }
            },
            onLeave: function (retval) {
                if (cnt.m <= 12) {
                    var r = readMaybeStr(retval);
                    console.log("[MSEC-OUT] #" + cnt.m + " ret=" + (r ? r.substring(0, 700) : "null"));
                }
            }
        });
        console.log("[metasec 28065c] hooked");
    } catch (e) { console.log("[metasec 28065c] fail: " + e); }
} else {
    console.log("[metasec] lib not loaded yet");
}

// 2a) 47aae4 (MOV X0,X21, BLR 前一条): 读 X21/X22 = 回调入参
try {
    Interceptor.attach(sbase.add(0x47aae4), {
        onEnter: function (args) {
            cnt.blr++;
            if (cnt.blr <= 12) {
                var a = readMaybeStr(this.context.x21);
                var b = readMaybeStr(this.context.x22);
                console.log("[BLR-ARG] #" + cnt.blr +
                    " X21=" + (a ? a.substring(0, 200) : "?") +
                    " X22=" + (b ? b.substring(0, 300) : "?"));
            }
        }
    });
    console.log("[47aae4] hooked");
} catch (e) { console.log("[47aae4] fail: " + e); }

// 2b) 47aafc (CBZ X21, BLR 后): 读 X21 = 回调返回值
try {
    Interceptor.attach(sbase.add(0x47aafc), {
        onEnter: function (args) {
            cnt.blr2++;
            if (cnt.blr2 <= 12) {
                var r = readMaybeStr(this.context.x21);
                console.log("[BLR-RET] #" + cnt.blr2 + " ret=" + (r ? r.substring(0, 700) : "null"));
            }
        }
    });
    console.log("[47aafc] hooked");
} catch (e) { console.log("[47aafc] fail: " + e); }

// 3) SetHeader 过滤 (八神名值对, 每请求一组已够)
try {
    Interceptor.attach(sbase.add(0x37ed64), {
        onEnter: function (args) {
            var name = readStdString(args[1]);
            if (name && isGod(name)) {
                cnt.shgod++;
                var val = readStdString(args[2]);
                console.log("[SET-GOD] #" + cnt.shgod + " " + name + "=" + (val ? val.substring(0, 120) : "?"));
            }
        }
    });
    console.log("[37ed64 SetHeader] hooked");
} catch (e) { console.log("[37ed64] fail: " + e); }

// 4) 心跳
setInterval(function () {
    console.log("[beat] m=" + cnt.m + " blr=" + cnt.blr + " blr2=" + cnt.blr2 + " shgod=" + cnt.shgod);
}, 15000);

console.log("[dy_hook17] loaded");

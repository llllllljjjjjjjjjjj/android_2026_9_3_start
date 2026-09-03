// 抖音 38.0.0 八神抓取 v19 (frida 16.5.7, ES5, attach 模式)
// 修复 v18: hexdump 是 QuickJS 保留名 → toHex
// 新增: metasec+28065c 运行时反汇编 (VMP 代码运行时已解密, 看真实指令)
//   + SET-GOD backtrace 调用链

function toHex(p, n) {
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

function disasmAt(p, n) {
    try {
        for (var i = 0; i < n; i++) {
            var ins = Instruction.parse(p);
            console.log("[M-DIS] " + p.sub(mbase).toString(16) + "  " + ins.mnemonic + "  " + ins.opStr);
            p = p.add(ins.size);
        }
    } catch (e) { console.log("[M-DIS] stop: " + e); }
}

var sbase = Module.findBaseAddress("libsscronet.so");
var mbase = Module.findBaseAddress("libmetasec_ml.so");
console.log("[base] sscronet=" + sbase + " metasec=" + mbase);

var cnt = { m: 0, shgod: 0, bt: 0 };

// 0) 立即: metasec+28065c 运行时字节 + 反汇编
if (mbase) {
    try {
        var p0 = mbase.add(0x28065c);
        console.log("[M-HEX28065c] " + toHex(p0, 512));
        disasmAt(p0, 60);
    } catch (e) { console.log("[M-DIS] fail: " + e); }
} else {
    console.log("[metasec] lib not loaded");
}

// 1) SetHeader: 八神 → value + backtrace
try {
    Interceptor.attach(sbase.add(0x37ed64), {
        onEnter: function (args) {
            var name = readStdString(args[1]);
            if (name && isGod(name)) {
                cnt.shgod++;
                var val = tryRead(args[2]);
                console.log("[SET-GOD] #" + cnt.shgod + " " + name + "=" + (val ? val.substring(0, 120) : "?"));
                if (cnt.bt < 6) {
                    cnt.bt++;
                    try {
                        var bts = Thread.backtrace(this.context, Backtracer.ACCURATE);
                        var out = [];
                        for (var i = 0; i < Math.min(bts.length, 7); i++) {
                            var mm = Process.findModuleByAddress(bts[i]);
                            out.push(mm ? mm.name + "+" + bts[i].sub(mm.base).toString(16) : String(bts[i]));
                        }
                        console.log("[SET-BT] #" + cnt.bt + " " + out.join(" <- "));
                    } catch (e) { console.log("[SET-BT] ERR " + e); }
                }
            }
        }
    });
    console.log("[37ed64] hooked");
} catch (e) { console.log("[37ed64] fail: " + e); }

// 2) metasec 回调: 入参出参 hex (前 8 次)
if (mbase) {
    try {
        Interceptor.attach(mbase.add(0x28065c), {
            onEnter: function (args) {
                cnt.m++;
                if (cnt.m <= 8) {
                    console.log("[MSEC-IN] #" + cnt.m +
                        " X0h=" + toHex(args[0], 48).substring(0, 96) +
                        " X0s=" + (tryRead(args[0]) ? tryRead(args[0]).substring(0, 80) : "?") +
                        " X1h=" + toHex(args[1], 48).substring(0, 96) +
                        " X1s=" + (tryRead(args[1]) ? tryRead(args[1]).substring(0, 80) : "?"));
                }
            },
            onLeave: function (retval) {
                if (cnt.m <= 8) {
                    console.log("[MSEC-OUT] #" + cnt.m +
                        " reth=" + toHex(retval, 64).substring(0, 128) +
                        " rets=" + (tryRead(retval) ? tryRead(retval).substring(0, 200) : "?"));
                }
            }
        });
        console.log("[metasec 28065c] hooked");
    } catch (e) { console.log("[metasec 28065c] fail: " + e); }
}

// 3) 心跳
setInterval(function () {
    console.log("[beat] m=" + cnt.m + " shgod=" + cnt.shgod + " bt=" + cnt.bt);
}, 15000);

console.log("[dy_hook19] loaded");

// 抖音 38.0.0 八神抓取 v14 (frida 16.5.7, ES5, attach 模式)
// 页保护绕行: 只 hook 412680 (已验证可写), 纯内存读解出神头写入函数地址
//   X19 = args[0] = URLRequest
//   [X19+8] = 内部对象 → [+0x40] → [+0x28] = ctx (网络上下文)
//   [ctx] = vtable → [+0x18] = ★神头写入虚方法

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

function godHeaders(ptr) {
    try {
        var begin = ptr.readPointer();
        var end = ptr.add(8).readPointer();
        var diff = end.sub(begin);
        if (diff.toInt32() < 0 || diff.toInt32() > 0x6000) return "(bad)";
        var out = [], i = 0, q = begin;
        var GOD = ["x-argus", "x-gorgon", "x-ladon", "x-khronos", "x-helios",
                   "x-medusa", "x-soter", "x-perseus", "x-tython", "x-ss-stub", "x-bogus"];
        while (q.compare(end) < 0 && i < 40) {
            var name = readStdString(q);
            if (name) {
                for (var g = 0; g < GOD.length; g++) {
                    if (name.toLowerCase().indexOf(GOD[g]) === 0) {
                        var val = readStdString(q.add(0x18));
                        out.push(name + "=" + (val ? val.substring(0, 60) : "?"));
                        break;
                    }
                }
            }
            q = q.add(0x30); i++;
        }
        return out.length ? out.join(" ") : "(no-gods)";
    } catch (e) { return "ERR:" + e; }
}

var done = {};
var cnt = { e: 0 };
var seenFns = {};

function tryHook680() {
    var base = Module.findBaseAddress("libsscronet.so");
    if (!base || done.h680) return;
    done.h680 = true;
    try {
        Interceptor.attach(base.add(0x412680), {
            onEnter: function (args) {
                cnt.e++;
                try {
                    var x19 = args[0];
                    var p = x19.add(8).readPointer();       // [X19+8]
                    var q = p.add(0x40).readPointer();      // [p+0x40]
                    var ctx = q.add(0x28).readPointer();    // [q+0x28] = ctx
                    var vt = ctx.readPointer();             // vtable
                    var fn = vt.add(0x18).readPointer();    // ★ 写入函数
                    var m = Process.findModuleByAddress(fn);
                    var loc = m ? m.name + "+" + fn.sub(m.base).toString(16) : String(fn);
                    if (!seenFns[loc]) {
                        seenFns[loc] = true;
                        console.log("[GODFN] vtable+0x18 = " + fn + " => " + loc +
                            " (ctx=" + ctx + " vt=" + vt + ")");
                    }
                    if (cnt.e <= 6) {
                        console.log("[412680-E] #" + cnt.e + " hdr: " + godHeaders(x19.add(0x358)));
                    }
                } catch (e) {
                    console.log("[412680-E] deref ERR: " + e);
                }
            }
        });
        console.log("[412680] hooked");
    } catch (e) { console.log("[412680] fail: " + e); }
}

tryHook680();
console.log("[dy_hook14] loaded");

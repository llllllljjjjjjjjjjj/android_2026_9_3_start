// 抖音 38.0.0 八神抓取 v15 (frida 16.5.7, ES5, attach 模式)
// 加心跳 (验证 gum 事件循环活着) + 412680/4127ac/411e74 三点 hook
// 411e74 onEnter 解引用拿 ctx vtable+0x18 = 神头写入函数

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

var base = Module.findBaseAddress("libsscronet.so");
console.log("[base] libsscronet = " + base);

var cnt = { e: 0, e74: 0, ac: 0 };
var seenFns = {};

// 1) 412680: 解引用拿写入函数
try {
    Interceptor.attach(base.add(0x412680), {
        onEnter: function (args) {
            cnt.e++;
            try {
                var x19 = args[0];
                var p = x19.add(8).readPointer();
                var q = p.add(0x40).readPointer();
                var ctx = q.add(0x28).readPointer();
                var vt = ctx.readPointer();
                var fn = vt.add(0x18).readPointer();
                var m = Process.findModuleByAddress(fn);
                var loc = m ? m.name + "+" + fn.sub(m.base).toString(16) : String(fn);
                if (!seenFns[loc]) {
                    seenFns[loc] = true;
                    console.log("[GODFN] vtable+0x18 = " + fn + " => " + loc + " (ctx=" + ctx + ")");
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

// 2) 4127ac: 验证请求路径活性
try {
    Interceptor.attach(base.add(0x4127ac), {
        onEnter: function (args) {
            cnt.ac++;
            if (cnt.ac <= 5) console.log("[4127ac-E] #" + cnt.ac);
        }
    });
    console.log("[4127ac] hooked");
} catch (e) { console.log("[4127ac] fail: " + e); }

// 3) 411e74: onEnter 时读 ctx (X19 已 MOV 完, 在 411e98 BL 之前)
try {
    Interceptor.attach(base.add(0x411e74), {
        onEnter: function (args) {
            cnt.e74++;
            if (cnt.e74 <= 5) console.log("[411e74-E] #" + cnt.e74);
            try {
                var x19 = args[0];
                var p = x19.add(8).readPointer();
                var q = p.add(0x40).readPointer();
                var ctx = q.add(0x28).readPointer();
                var vt = ctx.readPointer();
                var fn = vt.add(0x18).readPointer();
                var m = Process.findModuleByAddress(fn);
                var loc = m ? m.name + "+" + fn.sub(m.base).toString(16) : String(fn);
                if (!seenFns[loc]) {
                    seenFns[loc] = true;
                    console.log("[GODFN-411] vtable+0x18 = " + fn + " => " + loc);
                }
            } catch (e) { /* 静默 */ }
        }
    });
    console.log("[411e74] hooked");
} catch (e) { console.log("[411e74] fail: " + e); }

// 4) 心跳: 每 15s 证明事件循环活着
var beat = 0;
setInterval(function () {
    beat++;
    console.log("[beat] #" + beat + " cnt(680=" + cnt.e + ", e74=" + cnt.e74 + ", ac=" + cnt.ac + ")");
}, 15000);

console.log("[dy_hook15] loaded");

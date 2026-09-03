// 抖音 38.0.0 八神抓取 v13 (frida 16.5.7, ES5, attach 模式)
// 3411dc hook 失败 (341000 页受保护) → 绕开:
// hook 411f84 (BL 3411b4 调用点, 411000 页可写):
//   onEnter: X0=X21=ctx 对象, X1=X22, X2=X20=头容器, X3=回调结构
//   → 读 [X21]+0x18 = 神头写入虚方法地址 (与 3411b4 内 BLR 相同的 vtable)
// + 412680 onEnter 容器 dump (验证神头已写入)

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
var cnt = { w: 0 };
var seenFns = {};

function tryHook411f84() {
    var base = Module.findBaseAddress("libsscronet.so");
    if (!base || done.f84) return;
    done.f84 = true;
    try {
        Interceptor.attach(base.add(0x411f84), {
            onEnter: function (args) {
                this.ctx = this.context.x0;   // X21 = ctx 对象
                this.x2 = this.context.x2;    // 头容器
            },
            onLeave: function (ret) {
                try {
                    var vt = this.ctx.readPointer();      // vtable
                    var fn = vt.add(0x18).readPointer();  // 写入虚方法
                    var m = Process.findModuleByAddress(fn);
                    var loc = m ? m.name + "+" + fn.sub(m.base).toString(16) : String(fn);
                    cnt.w++;
                    if (!seenFns[loc]) {
                        seenFns[loc] = true;
                        console.log("[GODFN] vtable+0x18 = " + fn + " => " + loc);
                    }
                    if (cnt.w <= 8) {
                        console.log("[411f84-L] #" + cnt.w + " hdr-after-call: " + godHeaders(this.x2) + " ret=" + ret);
                    }
                } catch (e) { console.log("[411f84-L] ERR " + e); }
            }
        });
        console.log("[411f84] hooked");
    } catch (e) { console.log("[411f84] fail: " + e); }
}

function tryHook412680() {
    var base = Module.findBaseAddress("libsscronet.so");
    if (!base || done.h680) return;
    done.h680 = true;
    try {
        Interceptor.attach(base.add(0x412680), {
            onEnter: function (args) {
                if (cnt.w <= 8) {
                    console.log("[412680-E] hdr: " + godHeaders(args[0].add(0x358)));
                }
            }
        });
        console.log("[412680] hooked");
    } catch (e) { console.log("[412680] fail: " + e); }
}

tryHook411f84();
tryHook412680();
console.log("[dy_hook13] loaded");

// 抖音 38.0.0 八神抓取 v11 (frida 16.5.7, ES5, attach 模式)
// 定位神头写入阶段: 对比 411e74 / 412680 / 4127ac 三点的容器状态
// + 411e74 深 backtrace (20帧) 找外层生成器
// 容器 = X19+0x358; URLRequest = X19

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

// 只返回神头部分 (x-argus 等), 避免日志爆炸
function godHeaders(ptr) {
    try {
        var begin = ptr.readPointer();
        var end = ptr.add(8).readPointer();
        var diff = end.sub(begin);
        if (diff.toInt32() < 0 || diff.toInt32() > 0x6000) return null;
        var out = [], i = 0, q = begin;
        var GOD = ["x-argus", "x-gorgon", "x-ladon", "x-khronos", "x-helios",
                   "x-medusa", "x-soter", "x-perseus", "x-tython", "x-ss-stub", "x-bogus"];
        while (q.compare(end) < 0 && i < 40) {
            var name = readStdString(q);
            if (name) {
                for (var g = 0; g < GOD.length; g++) {
                    if (name.toLowerCase().indexOf(GOD[g]) === 0) {
                        var val = readStdString(q.add(0x18));
                        out.push(name + "=" + (val ? val.substring(0, 80) : "?"));
                        break;
                    }
                }
            }
            q = q.add(0x30); i++;
        }
        return out.length ? out.join(" ") : "(no-gods)";
    } catch (e) { return "ERR:" + e; }
}

function bt(ctx, n) {
    var s = "";
    try {
        var frames = Thread.backtrace(ctx, Backtracer.ACCURATE).slice(0, n || 20);
        frames.forEach(function (addr) {
            var m = Process.findModuleByAddress(addr);
            if (m) s += " " + m.name + "+" + addr.sub(m.base).toString(16);
            else s += " " + addr;
        });
    } catch (e) { s = " BTERR"; }
    return s;
}

var done = {};
var cnt = { e: 0 };

function hook411e74() {
    var base = Module.findBaseAddress("libsscronet.so");
    if (!base || done.h411) return;
    done.h411 = true;
    try {
        // 411e74 = 回调函数起点; onEnter 读 X19 容器
        Interceptor.attach(base.add(0x411e74), {
            onEnter: function (args) {
                cnt.e++;
                var h = godHeaders(this.context.x19.add(0x358));
                console.log("[411e74-E] #" + cnt.e + " " + h);
                if (cnt.e % 20 === 1) {
                    console.log("[411e74-BT] " + bt(this.context, 20));
                }
            }
        });
        console.log("[411e74] hooked");
    } catch (e) { console.log("[411e74] fail: " + e); }
}

function hook412680() {
    var base = Module.findBaseAddress("libsscronet.so");
    if (!base || done.h680) return;
    done.h680 = true;
    try {
        // 412680 = MaybeStartTransactionInternal; X0 = URLRequest?
        Interceptor.attach(base.add(0x412680), {
            onEnter: function (args) {
                var x0c = godHeaders(args[0].add(0x358));
                var x1c = godHeaders(args[1].add(0x358));
                console.log("[412680-E] x0:" + x0c + " | x1:" + x1c);
            }
        });
        console.log("[412680] hooked");
    } catch (e) { console.log("[412680] fail: " + e); }
}

function hook4127() {
    var base = Module.findBaseAddress("libsscronet.so");
    if (!base || done.h4127) return;
    done.h4127 = true;
    try {
        Interceptor.attach(base.add(0x4127ac), {
            onEnter: function (args) {
                var h = godHeaders(args[0].add(0x358));
                console.log("[4127ac-E] " + h);
            }
        });
        console.log("[4127ac] hooked");
    } catch (e) { console.log("[4127ac] fail: " + e); }
}

var timer = setInterval(function () {
    hook411e74();
    hook412680();
    hook4127();
}, 150);
console.log("[dy_hook11] loaded");

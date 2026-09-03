// 抖音 38.0.0 八神抓取 v12 (frida 16.5.7, ES5, attach 模式)
// hook 3411dc (BLR X9 = 神头写入虚方法调用点):
//   onEnter 拿 X9 = 写入函数地址 + 容器 before
//   onLeave 容器 after → 确认神头由该虚方法写入

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

function hookWrite() {
    var base = Module.findBaseAddress("libsscronet.so");
    if (!base || done.w) return;
    done.w = true;
    try {
        Interceptor.attach(base.add(0x3411dc), {
            onEnter: function (args) {
                this.x2saved = this.context.x2;
                this.target = this.context.x9;
                var m = Process.findModuleByAddress(this.target);
                var loc = m ? m.name + "+" + this.target.sub(m.base).toString(16) : String(this.target);
                cnt.w++;
                if (cnt.w <= 10 || cnt.w % 50 == 1) {
                    console.log("[GODW-E] #" + cnt.w + " fn=" + loc + " ctx=" + this.context.x0 +
                        " hdr-before: " + godHeaders(this.x2saved));
                }
            },
            onLeave: function (ret) {
                if (cnt.w <= 10 || cnt.w % 50 == 1) {
                    console.log("[GODW-L] #" + cnt.w + " hdr-after: " + godHeaders(this.x2saved) +
                        " ret=" + ret);
                }
            }
        });
        console.log("[3411dc] hooked");
    } catch (e) { console.log("[3411dc] fail: " + e); }
}

// 同时 hook 412680 确认参数流
function hook680() {
    var base = Module.findBaseAddress("libsscronet.so");
    if (!base || done.h680) return;
    done.h680 = true;
    try {
        Interceptor.attach(base.add(0x412680), {
            onEnter: function (args) {
                if (cnt.w <= 10) {
                    console.log("[412680-E] x0=" + args[0] + " x1=" + args[1] +
                        " hdr: " + godHeaders(args[0].add(0x358)));
                }
            }
        });
        console.log("[412680] hooked");
    } catch (e) { console.log("[412680] fail: " + e); }
}

// attach 到运行中进程, 库已加载 → 同步安装 (不用轮询; attach 模式下 gumjs 事件循环可能被 App 阻塞)
hookWrite();
hook680();
console.log("[dy_hook12] loaded");

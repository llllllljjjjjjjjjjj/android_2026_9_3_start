// 抖音 38.0.0 八神抓取 v9 (frida 16.5.7, ES5)
// 修正: 头容器 = X19+0x358 ({begin@0,end@8}, 元素0x30={name,value})
// 1) 4127ac onEnter/onLeave 全容器 dump 对比 (旧神头删除效果 + 新头是否写入)
// 2) SetHeader 流
// 3) 411e74: BL loc_3411B4 返回 W20 (成功/失败路径)

var SIG_KEYS = ["x-argus", "x-gorgon", "x-ladon", "x-khronos", "x-helios", "x-medusa",
    "x-soter", "x-perseus", "x-tython", "x-ss-stub", "x-bogus"];

function isSigKey(k) {
    if (!k) return false;
    for (var i = 0; i < SIG_KEYS.length; i++) if (k === SIG_KEYS[i]) return true;
    return k.indexOf("x-metasec") === 0;
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

function dumpContainer(ptr) {
    // ptr = {begin,end} 容器对象
    try {
        var begin = ptr.readPointer();
        var end = ptr.add(8).readPointer();
        var diff = end.sub(begin);
        if (diff.toInt32() < 0 || diff.toInt32() > 0x6000) return null;
        var out = [], i = 0, q = begin;
        while (q.compare(end) < 0 && i < 40) {
            var name = readStdString(q);
            var val = readStdString(q.add(0x18));
            out.push(name + (val ? "=" + val.substring(0, 60) : ""));
            q = q.add(0x30); i++;
        }
        return "(" + diff + ") " + out.join(" | ");
    } catch (e) { return "ERR:" + e; }
}

function readKV(p) {
    try {
        var ptr = p.readPointer();
        var len = p.add(8).readS64();
        if (len > 0 && len < 4096) return ptr.readUtf8String(len);
    } catch (e) { }
    return null;
}

var done = {};
var cnt = { e: 0, l: 0 };

function hook4127() {
    var base = Module.findBaseAddress("libsscronet.so");
    if (!base || done.h4127) return;
    done.h4127 = true;
    try {
        Interceptor.attach(base.add(0x4127ac), {
            onEnter: function (args) {
                cnt.e++;
                this.x19 = args[0];
                this.dump = (cnt.e % 15 === 1);
                if (this.dump) {
                    var c = dumpContainer(this.x19.add(0x358));
                    console.log("[4127E] #" + cnt.e + " hdr " + c);
                }
            },
            onLeave: function (retval) {
                cnt.l++;
                if (!this.dump) return;
                var c = dumpContainer(this.x19.add(0x358));
                console.log("[4127L] #" + cnt.l + " hdr " + c);
            }
        });
        console.log("[4127ac] hooked");
    } catch (e) { console.log("[4127ac] fail: " + e); }
}

function hookSet() {
    var base = Module.findBaseAddress("libsscronet.so");
    if (!base || done.set) return;
    done.set = true;
    try {
        Interceptor.attach(base.add(0x37ed64), {
            onEnter: function (args) {
                try {
                    var kp = args[1].readPointer();
                    var kl = args[1].add(8).readS64();
                    var key = (kl > 0 && kl < 200) ? kp.readUtf8String(kl) : null;
                    if (key && isSigKey(key)) {
                        var val = readKV(args[2]);
                        console.log("[SETHDR] " + key + " => " + (val ? val.substring(0, 400) : "?"));
                    }
                } catch (e) { }
            }
        });
        console.log("[sethdr] hooked");
    } catch (e) { console.log("[sethdr] fail: " + e); }
}

function hook411e74() {
    var base = Module.findBaseAddress("libsscronet.so");
    if (!base || done.h411) return;
    done.h411 = true;
    try {
        // BL loc_3411B4 的返回地址 411f88: 读 W20 看成功/失败
        Interceptor.attach(base.add(0x411f88), {
            onEnter: function (args) {
                var w20 = this.context.x20.toInt32();
                console.log("[411f88] 3411B4 returned w20=" + w20 + " (x19=" + this.context.x19 + ")");
            }
        });
        console.log("[411e74] hooked");
    } catch (e) { console.log("[411e74] fail: " + e); }
}

var timer = setInterval(function () {
    hook4127();
    hookSet();
    hook411e74();
}, 150);
console.log("[dy_hook9] loaded");

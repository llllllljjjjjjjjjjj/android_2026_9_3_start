// 抖音 38.0.0 八神抓取 v10 (frida 16.5.7, ES5)
// 在 v9 基础上新增:
// 1) SetHeader 写入神头时打完整 backtrace → 定位生成器所在模块+偏移
// 2) 魔改 Cronet API 表 (0x5d4f00-0x5d5600) 全槽采样: 首次调用打 backtrace
// 3) 保留 4127ac 容器对比 + 411f88 W20 路径判定

var SIG_KEYS = ["x-argus", "x-gorgon", "x-ladon", "x-khronos", "x-helios", "x-medusa",
    "x-soter", "x-perseus", "x-tython", "x-ss-stub", "x-bogus", "x-ttnet",
    "x-tea", "x-hunter"];

function isSigKey(k) {
    if (!k) return false;
    for (var i = 0; i < SIG_KEYS.length; i++) if (k.indexOf(SIG_KEYS[i]) === 0) return true;
    return false;
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

// backtrace: 前 12 帧 → "mod+off mod+off ..."
function bt(ctx) {
    var s = "";
    try {
        var frames = Thread.backtrace(ctx, Backtracer.ACCURATE).slice(0, 12);
        frames.forEach(function (addr) {
            var m = Process.findModuleByAddress(addr);
            if (m) s += " " + m.name + "+" + addr.sub(m.base).toString(16);
            else s += " " + addr;
        });
    } catch (e) { s = " BTERR:" + e; }
    return s;
}

var done = {};
var cnt = { e: 0, l: 0, set: 0 };

// ---- 1) SetHeader 神头写入 backtrace ----
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
                        cnt.set++;
                        var val = readKV(args[2]);
                        console.log("[SETHDR#" + cnt.set + "] " + key + " => " + (val ? val.substring(0, 200) : "?") + bt(this.context));
                    }
                } catch (e) { }
            }
        });
        console.log("[sethdr] hooked");
    } catch (e) { console.log("[sethdr] fail: " + e); }
}

// ---- 2) 4127ac 容器对比 (删除旧神头) ----
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

// ---- 3) 411f88 W20 路径判定 ----
function hook411f88() {
    var base = Module.findBaseAddress("libsscronet.so");
    if (!base || done.h411) return;
    done.h411 = true;
    try {
        Interceptor.attach(base.add(0x411f88), {
            onEnter: function (args) {
                var w20 = this.context.x20.toInt32();
                console.log("[411f88] 3411B4 returned w20=" + w20);
            }
        });
        console.log("[411f88] hooked");
    } catch (e) { console.log("[411f88] fail: " + e); }
}

// ---- 4) 魔改 Cronet API 表采样 (0x5d4f00-0x5d5600 槽) ----
// 表槽 = 绝对函数指针 (重定位后), 首次调用打 backtrace, 之后每 200 次打摘要
function hookApiTable() {
    var base = Module.findBaseAddress("libsscronet.so");
    if (!base || done.api) return;
    done.api = true;
    var stats = {};
    for (var ea = 0x5d4f00; ea < 0x5d5600; ea += 8) {
        (function (slot) {
            try {
                var fn = base.add(slot).readPointer();
                if (fn.isNull()) return;
                // 校验指向模块内合理函数
                var m = Process.findModuleByAddress(fn);
                if (!m || m.name !== "libsscronet.so") return;
                var off = fn.sub(base);
                if (off.toInt32() < 0x1000 || off.toInt32() > 0x600000) return;
                stats[slot] = { hits: 0 };
                Interceptor.attach(fn, {
                    onEnter: function (args) {
                        var st = stats[slot];
                        st.hits++;
                        if (st.hits === 1) {
                            console.log("[API@0x" + slot.toString(16) + "->0x" + off.toString(16) + "] FIRST" + bt(this.context));
                        } else if (st.hits % 200 === 0) {
                            console.log("[API@0x" + slot.toString(16) + "->0x" + off.toString(16) + "] hits=" + st.hits);
                        }
                    }
                });
            } catch (e) { }
        })(ea);
    }
    var n = Object.keys(stats).length;
    console.log("[api-table] hooked " + n + " slots");
}

var timer = setInterval(function () {
    hookSet();
    hook4127();
    hook411f88();
    hookApiTable();
}, 150);
console.log("[dy_hook10] loaded");

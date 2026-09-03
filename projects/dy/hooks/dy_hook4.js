// 抖音 38.0.0 八神签名抓取 v4 (frida 16.5.7, ES5)
// v3 结论: 4127ac 很少被调用(~2次/120s); sub_204CC0 是通用头分发器(很多 LR)
// 本版: 4127ac 槽表用固定栈偏移(sp-0x3A0)读取; gen 只关注 4127ac 的 6 个调用点;
//       每次 4127ac 调用都扫请求对象找 URL

function readCString(p, max) {
    try { return p.readUtf8String(max || 300); } catch (e) { return null; }
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
        if (len > 0 && len < 2048) {
            var s = ptr.readUtf8String(len);
            var ok = true;
            for (var i = 0; i < s.length; i++) { var c = s.charCodeAt(i); if (c < 0x20 || c > 0x7e) { ok = false; break; } }
            return ok ? s : null;
        }
    } catch (e) { }
    return null;
}

function hexdump8(p, n) {
    var s = "";
    for (var i = 0; i < n; i++) {
        var b = p.add(i).readU8();
        s += (b < 16 ? "0" : "") + b.toString(16) + " ";
    }
    return s;
}

var SLOTS = { 0x288: "x-ss-dp", 0x2A0: "x-tt-bypass-dp", 0x2B8: "x-ss-req-ticket",
    0x2D0: "x-vc-bdturing", 0x2E8: "x-khronos", 0x300: "x-gorgon", 0x318: "x-ladon",
    0x330: "x-tython", 0x348: "x-argus" };

var GEN_SITES = { "412aa8": 1, "412b08": 1, "412c38": 1, "412df4": 1, "412dfc": 1, "412ef8": 1 };

var done = { n4127: 0, n204: 0, n37f: 0 };

function scanUrlObj(p, tag) {
    try {
        var found = {};
        var targets = [p];
        try { targets.push(p.add(8).readPointer()); } catch (e) { }
        try { targets.push(p.add(0x1E0).readPointer()); } catch (e) { }
        try { targets.push(p.add(0x518).readPointer()); } catch (e) { }
        for (var t = 0; t < targets.length; t++) {
            if (targets[t].isNull()) continue;
            for (var off = 0; off < 0x2000; off += 8) {
                try {
                    var ptr = targets[t].add(off).readPointer();
                    var cs = readCString(ptr, 400);
                    if (cs && (cs.indexOf("http") === 0 || cs.indexOf("/aweme") >= 0) && cs.length < 400) {
                        if (!found[cs]) { found[cs] = 1; console.log("[" + tag + "] URL " + cs); }
                    }
                } catch (e) { }
            }
        }
    } catch (e) { }
}

// ---- Java 层 ----
Java.perform(function () {
    try {
        var Mod = Java.use("java.lang.reflect.Modifier");
        var y2 = Java.use("ms.bd.c.y2");
        var methods = y2.class.getDeclaredMethods();
        for (var i = 0; i < methods.length; i++) {
            var m = methods[i];
            if (Mod.isStatic(m.getModifiers()) && Mod.isNative(m.getModifiers()) && m.getParameterTypes().length === 5) {
                var mname = m.getName();
                (function (mn) {
                    y2[mn].overload('int', 'int', 'long', 'java.lang.String', 'java.lang.Object')
                        .implementation = function (i, i2, j, s, o) {
                            var r = this[mn](i, i2, j, s, o);
                            // 只打印非高频 id; 0x02/0x03 族打印 sub 变化
                            if (i === 33554445) { // 0x0200000D 轮询, 不刷屏
                            } else if (i === 16777217) { // 0x01000001 解密, 不刷屏
                            } else {
                                console.log("[Y2." + mn + "] id=" + i + " sub=" + i2 + " flag=" + j + " str=" + (s ? String(s).substring(0, 80) : "null") + " => " + (r ? r.$className + " " + String(r).substring(0, 80) : "null"));
                            }
                            return r;
                        };
                })(mname);
            }
        }
    } catch (e) { console.log("[Y2] fail: " + e); }
});

// ---- native ----
function hookCore() {
    var base = Module.findBaseAddress("libsscronet.so");
    if (!base) return;
    if (done.core) return;
    done.core = true;

    // 1. sub_204CC0: 只看 4127ac 的 6 个调用点
    Interceptor.attach(base.add(0x204cc0), {
        onEnter: function (args) {
            this.slot = args[0];
            this.lr = this.returnAddress.sub(base).toString(16);
            this.name = readStdString(this.slot);
            this.isGen = !!GEN_SITES[this.lr];
        },
        onLeave: function (retval) {
            done.n204++;
            if (!this.isGen) return;
            var v = readStdString(this.slot);
            var rv = null;
            try { if (!retval.isNull()) rv = readStdString(retval); } catch (e) { }
            console.log("[gen@+" + this.lr + "] in=" + (this.name || "?") + " out=" + (v || "?") +
                (rv ? " ret=" + rv : "") + " hex=" + hexdump8(this.slot, 24));
        }
    });
    console.log("[gen:204cc0] hooked");

    // 2. sub_37F078: 打印 LR + 值
    Interceptor.attach(base.add(0x37f078), {
        onEnter: function (args) {
            try {
                var vp = args[1].readPointer();
                var vl = args[1].add(8).readS64();
                var vs = (vl > 0 && vl < 2048) ? vp.readUtf8String(vl) : null;
                if (vs && vs.length > 1) {
                    var lr = this.returnAddress.sub(Module.findBaseAddress("libsscronet.so")).toString(16);
                    console.log("[asm@+" + lr + "] " + vs.substring(0, 300));
                }
            } catch (e) { }
        }
    });
    console.log("[asm:37f078] hooked");

    // 3. 0x4127ac: 槽表 = sp-0x3A0 (固定栈偏移), 每次调用全打印
    Interceptor.attach(base.add(0x4127ac), {
        onEnter: function (args) {
            this.x0 = args[0];
            this.sp = this.context.sp;
        },
        onLeave: function (retval) {
            done.n4127++;
            console.log("[4127ac] call #" + done.n4127 + " req=" + this.x0);
            var slotbase = this.sp.sub(0x3A0);
            var out = [];
            for (var k in SLOTS) {
                var p = slotbase.add(parseInt(k, 16));
                var v = readStdString(p);
                out.push(SLOTS[k] + "=" + (v ? v.substring(0, 400) : "HEX:" + hexdump8(p, 24)));
            }
            console.log("[4127ac] slots: " + out.join(" | "));
            // 生成结果长度字段
            try {
                console.log("[4127ac] objlen7A0=" + this.x0.add(0x7A0).readU32() + " objlen7A4=" + this.x0.add(0x7A4).readU32());
            } catch (e) { }
            scanUrlObj(this.x0, "req#" + done.n4127);
        }
    });
    console.log("[4127ac] hooked");
}

function hookMetasec() {
    var base = Module.findBaseAddress("libmetasec_ml.so");
    if (!base || done.ms) return;
    done.ms = true;
    try {
        Interceptor.attach(base.add(0x27e7f0), {
            onEnter: function (args) {
                console.log("[metasec] JNI_OnLoad vm=" + args[0] + " base=" + base);
            }
        });
        console.log("[metasec] JNI_OnLoad hooked");
    } catch (e) { console.log("[metasec] fail: " + e); }
}

var timer = setInterval(function () { hookCore(); hookMetasec(); }, 150);
console.log("[dy_hook4] loaded");

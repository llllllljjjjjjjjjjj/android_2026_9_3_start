// 抖音 38.0.0 八神签名抓取 v3 (frida 16.5.7, ES5)
// 核心: hook sub_204CC0 (每槽签名生成器) 抓 头名=>签名值 对拍
//      hook sub_37F078 (组装函数) 关联请求对象
//      libc++ std::string 解析 (SSO: [p+0x17]&0x80==0 则内联)

var HEADERS = ["x-gorgon", "x-ladon", "x-argus", "x-khronos", "x-soter", "x-medusa",
    "x-helios", "x-perseus", "x-ss-stub", "x-tython", "x-bd-client-key", "x-bogus",
    "x-ss-dp", "x-ss-req-ticket", "x-vc-bdturing-sdk-version", "x-tt-bypass-dp"];

function isPrintable(s) {
    if (!s) return false;
    for (var i = 0; i < s.length; i++) {
        var c = s.charCodeAt(i);
        if (c < 0x20 || c > 0x7e) return false;
    }
    return true;
}

function readCString(p, max) {
    try { return p.readUtf8String(max || 300); } catch (e) { return null; }
}

// libc++ std::string: [p]=ptr [p+8]=len [p+0x17]=SSO标志(最高位0=内联)
function readStdString(p) {
    try {
        var flag = p.add(0x17).readU8();
        if ((flag & 0x80) === 0) {
            // SSO 内联: 数据在 p, 长度=flag
            if (flag > 0 && flag < 23) {
                var s = p.readUtf8String(flag);
                return isPrintable(s) ? s : null;
            }
            return null;
        }
        var ptr = p.readPointer();
        var len = p.add(8).readS64();
        if (len > 0 && len < 2048) {
            var s = ptr.readUtf8String(len);
            return isPrintable(s) ? s : null;
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

// 槽是否是我们关注的头名槽
function isHeaderName(s) {
    if (!s) return false;
    for (var i = 0; i < HEADERS.length; i++) if (s === HEADERS[i]) return true;
    if (s.indexOf("x-") === 0 && s.length < 48) return true;
    return false;
}

var done = { n204: 0, n37f: 0, n4127: 0 };

// 在对象指针附近扫 URL（深扫: 对象本体 + [obj+8] + [obj+0x1E0] + [obj+0x518]）
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

// ---- Java 层: native 门 ms.bd.c.y2.a ----
Java.perform(function () {
    try {
        var Mod = Java.use("java.lang.reflect.Modifier");
        var y2 = Java.use("ms.bd.c.y2");
        var methods = y2.class.getDeclaredMethods();
        var hooked = false;
        for (var i = 0; i < methods.length; i++) {
            var m = methods[i];
            if (Mod.isStatic(m.getModifiers()) && Mod.isNative(m.getModifiers()) && m.getParameterTypes().length === 5) {
                var mname = m.getName();
                (function (mn) {
                    y2[mn].overload('int', 'int', 'long', 'java.lang.String', 'java.lang.Object')
                        .implementation = function (i, i2, j, s, o) {
                            var r = this[mn](i, i2, j, s, o);
                            // id=50331651: flag/ret 是指针形状 → 读指针内容
                            var extra = "";
                            try {
                                if (i === 50331651 || i === 33554445) {
                                    var fp = ptr("0x" + j.toString(16));
                                    var ss = readStdString(fp);
                                    var cs = readCString(fp, 300);
                                    extra = " flagPtr=" + fp + " stdStr=" + (ss || "?") + " cStr=" + (cs || "?");
                                }
                            } catch (e) { }
                            if (i !== 16777217 && i !== 67108865 && i !== 67108866) { // 高频解密/初始化不刷屏
                                console.log("[Y2." + mn + "] id=" + i + " sub=" + i2 + " flag=" + j + extra);
                            }
                            return r;
                        };
                })(mname);
                hooked = true;
            }
        }
        if (!hooked) console.log("[Y2] no match");
    } catch (e) { console.log("[Y2] fail: " + e); }
});

// ---- native 层 ----
function hookCore() {
    var base = Module.findBaseAddress("libsscronet.so");
    if (!base) return;
    if (done.core) return;
    done.core = true;

    // 1. sub_204CC0 每槽签名生成器: onEnter 槽=头名, onLeave 槽=值
    Interceptor.attach(base.add(0x204cc0), {
        onEnter: function (args) {
            this.slot = args[0];
            this.lr = this.returnAddress.sub(base).toString(16);
            var name = readStdString(this.slot);
            this.name = name;
            this.isHdr = isHeaderName(name);
        },
        onLeave: function (retval) {
            done.n204++;
            var v = readStdString(this.slot);
            var rv = null;
            try { if (!retval.isNull()) rv = readStdString(retval); } catch (e) { }
            if (this.isHdr && v && v !== this.name) {
                console.log("[gen@+" + this.lr + "] " + this.name + " => " + v);
            } else if ((v && v !== this.name) && (this.lr === "412df0" || this.lr === "412df8" || this.lr === "412ef4" || this.lr === "412b04")) {
                // 循环外调用点: 槽本来是空, 生成后非空 → 就是 x-argus 等
                console.log("[gen@+" + this.lr + "] (empty) => " + v + (rv ? " ret=" + rv : ""));
            } else if (this.isHdr && done.n204 % 500 === 0) {
                console.log("[gen@+" + this.lr + "] " + this.name + " NOCHANGE slot=" + hexdump8(this.slot, 24));
            }
            if (done.n204 % 1000 === 0) console.log("[gen] total=" + done.n204);
        }
    });
    console.log("[gen:204cc0] hooked");

    // 2. sub_37F078 组装: X0=请求对象 X1={ptr,len}
    Interceptor.attach(base.add(0x37f078), {
        onEnter: function (args) {
            this.obj = args[0];
            this.valp = args[1];
            try {
                var vp = this.valp.readPointer();
                var vl = this.valp.add(8).readS64();
                var vs = (vl > 0 && vl < 2048) ? vp.readUtf8String(vl) : null;
                if (vs && isPrintable(vs) && vs.length > 4) {
                    done.n37f++;
                    console.log("[asm] val=" + vs.substring(0, 400));
                    if (done.n37f % 20 === 1) scanUrlObj(this.obj, "asm.obj");
                }
            } catch (e) { }
        }
    });
    console.log("[asm:37f078] hooked");

    // 3. 0x4127ac 头构建: 槽表在栈上(SP+0x1A0), 用 "x-ss-dp" 字节定位后读 9 个签名槽
    var SLOTS = { 0x288: "x-ss-dp", 0x2A0: "x-tt-bypass-dp", 0x2B8: "x-ss-req-ticket",
        0x2D0: "x-vc-bdturing", 0x2E8: "x-khronos", 0x300: "x-gorgon", 0x318: "x-ladon",
        0x330: "x-tython", 0x348: "x-argus" };
    function findBytes(p, range, bytes) {
        for (var off = 0; off < range; off += 8) {
            try {
                var b = p.add(off).readByteArray(bytes.length);
                var arr = new Uint8Array(b), ok = true;
                for (var i = 0; i < bytes.length; i++) if (arr[i] !== bytes[i]) { ok = false; break; }
                if (ok) return off;
            } catch (e) { }
        }
        return -1;
    }
    Interceptor.attach(base.add(0x4127ac), {
        onEnter: function (args) {
            this.x0 = args[0];
            this.sp = this.context.sp;
        },
        onLeave: function (retval) {
            done.n4127++;
            if (done.n4127 % 10 !== 1) return;
            // 运行时定位槽表: 在栈窗口内找 "x-ss-dp"
            var bytes = [];
            for (var i = 0; i < 8; i++) bytes.push("x-ss-dp".charCodeAt(i));
            var off = findBytes(this.sp.sub(0x600), 0x600, bytes);
            if (off < 0) { if (done.n4127 === 1) console.log("[4127ac] slot table not found on stack"); return; }
            var slotbase = this.sp.sub(0x600).add(off - 0x288);
            var out = [];
            for (var k in SLOTS) {
                var v = readStdString(slotbase.add(parseInt(k, 16)));
                if (v) out.push(SLOTS[k] + "=" + v.substring(0, 500));
            }
            console.log("[4127ac] " + out.join(" | "));
            if (done.n4127 % 100 === 1) scanUrlObj(this.x0, "req");
        }
    });
    console.log("[4127ac] hooked");
}

// ---- metasec JNI_OnLoad ----
function hookMetasec() {
    var base = Module.findBaseAddress("libmetasec_ml.so");
    if (!base || done.ms) return;
    done.ms = true;
    try {
        Interceptor.attach(base.add(0x27e7f0), {
            onEnter: function (args) {
                console.log("[metasec] JNI_OnLoad vm=" + args[0]);
            }
        });
        console.log("[metasec] JNI_OnLoad hooked base=" + base);
    } catch (e) { console.log("[metasec] fail: " + e); }
}

var timer = setInterval(function () { hookCore(); hookMetasec(); }, 150);
console.log("[dy_hook3] loaded");

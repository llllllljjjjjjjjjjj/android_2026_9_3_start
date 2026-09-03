// 抖音 38.0.0 八神签名抓取 v2 (frida 16.5.7, ES5)
// 深度抓取 libsscronet 0x4127ac 头构建: dump 槽表值 + 请求上下文 URL

var HEADERS = ["x-gorgon", "x-ladon", "x-argus", "x-khronos", "x-soter", "x-medusa",
    "x-helios", "x-perseus", "x-ss-stub", "x-tython", "x-bd-client-key", "x-bogus"];

function readCString(p, max) {
    try { return p.readUtf8String(max || 200); } catch (e) { return null; }
}

// 在指针附近扫描已知头名，找到后打印名字和其后字符串
function scanStruct(p, tag) {
    var found = [];
    try {
        var range = 0x4000;
        var base = p.sub(0x200);
        for (var off = 0; off < range; off += 8) {
            for (var h = 0; h < HEADERS.length; h++) {
                var s = null;
                try {
                    var b = base.add(off).readByteArray(HEADERS[h].length);
                    var arr = new Uint8Array(b);
                    var ok = true;
                    for (var i = 0; i < arr.length; i++) {
                        if (arr[i] !== HEADERS[h].charCodeAt(i)) { ok = false; break; }
                    }
                    if (ok) s = HEADERS[h];
                } catch (e) { }
                if (s) {
                    // 名字后面的字符串值（可能隔 8 字节对齐指针）
                    var val = null;
                    for (var v = off + 16; v < off + 0x80; v += 8) {
                        var cand = base.add(v).readPointer();
                        var cs = readCString(cand, 300);
                        if (cs && cs.length > 2 && cs.length < 300) { val = cs; break; }
                    }
                    if (!val) {
                        var cs2 = readCString(base.add(off + 8), 200);
                        if (cs2 && cs2.length > 2) val = cs2;
                    }
                    found.push(s + "=" + (val || "?"));
                    off += HEADERS[h].length; // 跳过这个名字
                    break;
                }
            }
        }
    } catch (e) { }
    if (found.length) console.log("[" + tag + "] " + found.join(" | "));
}

function scanUrl(p, tag) {
    try {
        var range = 0x8000;
        var base = p;
        var urls = {};
        for (var off = 0; off < range; off += 4) {
            try {
                var ptr = base.add(off).readPointer();
                var cs = readCString(ptr, 300);
                if (cs && (cs.indexOf("http") === 0 || cs.indexOf("/aweme") >= 0) && cs.length < 300) {
                    if (!urls[cs]) {
                        urls[cs] = 1;
                        console.log("[" + tag + "] URL " + cs);
                    }
                }
            } catch (e) { }
        }
    } catch (e) { }
}

var done = {};

Java.perform(function () {
    // ---- 1. native 门 ms.bd.c.y2.a ----
    try {
        var Mod = Java.use("java.lang.reflect.Modifier");
        var y2 = Java.use("ms.bd.c.y2");
        var methods = y2.class.getDeclaredMethods();
        var hooked = false;
        for (var i = 0; i < methods.length; i++) {
            var m = methods[i];
            if (Mod.isStatic(m.getModifiers()) && Mod.isNative(m.getModifiers()) && m.getParameterTypes().length === 5) {
                var mname = m.getName();
                console.log("[Y2] static native:", mname);
                (function (mn) {
                    y2[mn].overload('int', 'int', 'long', 'java.lang.String', 'java.lang.Object')
                        .implementation = function (i, i2, j, s, o) {
                            var r = this[mn](i, i2, j, s, o);
                            var os = null;
                            try {
                                if (o !== null && o.$className) {
                                    if (o.$className === "[B") {
                                        var bb = Java.array('byte', o);
                                        var hx = "";
                                        for (var k = 0; k < Math.min(bb.length, 64); k++) hx += ("0" + (bb[k] & 255).toString(16)).slice(-2);
                                        os = "byte[" + bb.length + "] " + hx;
                                    } else os = o.$className + " " + String(o).substring(0, 120);
                                } else os = String(o);
                            } catch (e) { os = "?" + e; }
                            var rs = null;
                            try {
                                if (r !== null) {
                                    if (r.$className === "[B") {
                                        var rb = Java.array('byte', r);
                                        var hx2 = "";
                                        for (var k = 0; k < Math.min(rb.length, 64); k++) hx2 += ("0" + (rb[k] & 255).toString(16)).slice(-2);
                                        rs = "byte[" + rb.length + "] " + hx2;
                                    } else rs = r.$className + " " + String(r).substring(0, 120);
                                }
                            } catch (e) { }
                            console.log("[Y2." + mn + "] id=" + i + " sub=" + i2 + " flag=" + j + " str=" + (s || "null") + " obj=" + os + " => " + rs);
                            return r;
                        };
                })(mname);
                hooked = true;
            }
        }
        if (!hooked) console.log("[Y2] no match");
    } catch (e) { console.log("[Y2] fail: " + e); }

    // ---- 2. 实现类 p003X.C43160094s ----
    try {
        var Impl = Java.use("p003X.C43160094s");
        Impl.frameSign.overload('java.lang.String', 'int').implementation = function (str, i) {
            console.log("[Impl.frameSign] IN str=" + (str ? String(str).substring(0, 3000) : "null") + " i=" + i);
            var r = this.frameSign(str, i);
            var ks = r.keySet().toArray();
            var out = [];
            for (var k = 0; k < ks.length; k++) out.push(String(ks[k]) + "=" + String(r.get(ks[k])));
            console.log("[Impl.frameSign] OUT " + out.join(" | "));
            return r;
        };
        Impl.getFeatureHash.overload('java.lang.String', '[B').implementation = function (str, b) {
            console.log("[Impl.getFeatureHash] IN str=" + str + " b.len=" + (b ? b.length : 0));
            var r = this.getFeatureHash(str, b);
            var ks = r.keySet().toArray();
            var out = [];
            for (var k = 0; k < ks.length; k++) out.push(String(ks[k]) + "=" + String(r.get(ks[k])));
            console.log("[Impl.getFeatureHash] OUT " + out.join(" | "));
            return r;
        };
        Impl.getToken.implementation = function () {
            var r = this.getToken();
            console.log("[Impl.getToken] OUT " + r);
            return r;
        };
        Impl.getReportRaw.overload('java.lang.String', 'int', 'java.util.Map').implementation = function (s, i, m) {
            console.log("[Impl.getReportRaw] IN s=" + (s ? String(s).substring(0, 400) : "null") + " i=" + i);
            var r = this.getReportRaw(s, i, m);
            console.log("[Impl.getReportRaw] OUT " + (r ? String(r).substring(0, 500) : "null"));
            return r;
        };
        console.log("[Impl] hooked p003X.C43160094s");
    } catch (e) { console.log("[Impl] fail: " + e); }

    // ---- 3. MSManager 转发 ----
    try {
        var MM = Java.use("com.bytedance.mobsec.metasec.ml.MSManager");
        MM.frameSign.overload('java.lang.String', 'int').implementation = function (str, i) {
            console.log("[MM.frameSign] IN str=" + (str ? String(str).substring(0, 2000) : "null") + " i=" + i);
            var r = this.frameSign(str, i);
            var ks = r.keySet().toArray();
            var out = [];
            for (var k = 0; k < ks.length; k++) out.push(String(ks[k]) + "=" + String(r.get(ks[k])));
            console.log("[MM.frameSign] OUT " + out.join(" | "));
            return r;
        };
        console.log("[MM.frameSign] hooked");
    } catch (e) { console.log("[MM] fail: " + e); }
});

// ---- 4. libsscronet 0x4127ac 深度抓取 ----
function hookSscronet() {
    var base = Module.findBaseAddress("libsscronet.so");
    if (!base) return;
    if (done.ssc) return;
    try {
        Interceptor.attach(base.add(0x4127ac), {
            onEnter: function (args) {
                this.x0 = args[0];
                this.x2 = args[2];
            },
            onLeave: function (retval) {
                // 槽表在 x0 指向的结构（0x288 起）+ ret 容器
                scanStruct(this.x0, "4127ac.x0");
                if (!retval.isNull() && !retval.equals(this.x0)) scanStruct(retval, "4127ac.ret");
                // 每 20 次 dump 一次 URL 上下文
                this.n = (done.n || 0) + 1;
                done.n = this.n;
                if (this.n % 20 === 1) scanUrl(this.x2, "ctx");
            }
        });
        done.ssc = true;
        console.log("[sscronet:4127ac] hooked base=" + base);
    } catch (e) { console.log("[sscronet] fail: " + e); }
}

// ---- 5. metasec JNI_OnLoad ----
function hookMetasec() {
    var base = Module.findBaseAddress("libmetasec_ml.so");
    if (!base) return;
    if (done.ms) return;
    try {
        Interceptor.attach(base.add(0x27e7f0), {
            onEnter: function (args) {
                console.log("[metasec] JNI_OnLoad vm=" + args[0]);
                // 在 JNI_OnLoad 里抓 RegisterNatives：x0=vm, 方法表在之后 BLR 前 x2
                // 简化：JNI_OnLoad 返回后 hook 所有以 Java_ 注册？无。靠 IDA v2 表。
            }
        });
        done.ms = true;
        console.log("[metasec] JNI_OnLoad hooked base=" + base);
    } catch (e) { console.log("[metasec] fail: " + e); }
}

var timer = setInterval(function () { hookSscronet(); hookMetasec(); }, 150);
console.log("[dy_hook2] loaded");

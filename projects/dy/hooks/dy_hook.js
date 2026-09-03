// 抖音 38.0.0 八神签名抓取 (frida 16.5.7, ES5)
// 目标1: ms.bd.c.y2 的 static native 门 (jadx: AbstractC19436y2.m84216a)
// 目标2: com.bytedance.mobsec.metasec.ml.MSManager.frameSign(String,int)
// 目标3: libsscronet.so 0x4127ac (native 头构建) / libmetasec_ml.so JNI_OnLoad 0x27e7f0

function hexdump8(buf, n) {
    var s = "";
    var len = Math.min(buf.length, n || 128);
    for (var i = 0; i < len; i++) {
        var b = buf[i] & 0xFF;
        s += (b < 16 ? "0" : "") + b.toString(16) + " ";
    }
    return s;
}

function tryStr(o) {
    if (o === null || o === undefined) return "null";
    try {
        if (o.$className === "byte[]" || o.$className === "[B") {
            var bb = Java.array('byte', o);
            return "byte[" + bb.length + "] " + hexdump8(bb, 96);
        }
        return "(" + (o.$className || typeof o) + ") " + String(o);
    } catch (e) {
        return "?err:" + e;
    }
}

function mapStr(m) {
    try {
        var ks = m.keySet().toArray();
        var out = [];
        for (var i = 0; i < ks.length; i++) {
            var k = String(ks[i]);
            out.push(k + "=" + String(m.get(ks[i])));
        }
        return out.join(" | ");
    } catch (e) {
        return "map?err:" + e;
    }
}

var done = {};

Java.perform(function () {
    // ---- 1. native 门 ms.bd.c.y2.a(int,int,long,String,Object) ----
    try {
        var y2 = Java.use("ms.bd.c.y2");
        var methods = y2.class.getDeclaredMethods();
        var hooked = false;
        for (var i = 0; i < methods.length; i++) {
            var m = methods[i];
            var mods = m.getModifiers();
            if (java.lang.reflect.Modifier.isStatic(mods) && java.lang.reflect.Modifier.isNative(mods)) {
                var mname = m.getName();
                var nparams = m.getParameterTypes().length;
                if (nparams === 5) {
                    console.log("[Y2] static native method:", mname);
                    y2[mname].overload('int', 'int', 'long', 'java.lang.String', 'java.lang.Object')
                        .implementation = function (i, i2, j, s, o) {
                            var r = this[mname](i, i2, j, s, o);
                            console.log("[Y2." + mname + "] id=" + i + " sub=" + i2 + " flag=" + j + " str=" + s + " obj=" + tryStr(o));
                            console.log("[Y2." + mname + "] RET=" + tryStr(r));
                            return r;
                        };
                    hooked = true;
                }
            }
        }
        if (!hooked) console.log("[Y2] no 5-param static native found");
    } catch (e) { console.log("[Y2] hook fail: " + e); }

    // ---- 2. frameSign 接口入口 (MSManager 转发) ----
    try {
        var MM = Java.use("com.bytedance.mobsec.metasec.ml.MSManager");
        MM.frameSign.overload('java.lang.String', 'int').implementation = function (str, i) {
            console.log("[frameSign] IN str=" + (str ? String(str).substring(0, 2000) : "null") + " i=" + i);
            var r = this.frameSign(str, i);
            console.log("[frameSign] OUT " + mapStr(r));
            return r;
        };
        console.log("[frameSign] hooked on MSManager");
    } catch (e) { console.log("[frameSign] MSManager hook fail: " + e); }

    // ---- 3. getFeatureHash(String,byte[]) ----
    try {
        var MM = Java.use("com.bytedance.mobsec.metasec.ml.MSManager");
        MM.getFeatureHash.overload('java.lang.String', '[B').implementation = function (str, b) {
            console.log("[getFeatureHash] IN str=" + str + " b=" + tryStr(b));
            var r = this.getFeatureHash(str, b);
            console.log("[getFeatureHash] OUT " + mapStr(r));
            return r;
        };
        console.log("[getFeatureHash] hooked");
    } catch (e) { console.log("[getFeatureHash] fail: " + e); }

    // ---- 4. getReportRaw / getToken ----
    try {
        var MM = Java.use("com.bytedance.mobsec.metasec.ml.MSManager");
        MM.getToken.implementation = function () {
            var r = this.getToken();
            console.log("[getToken] OUT " + r);
            return r;
        };
        MM.getReportRaw.overload('java.lang.String', 'int', 'java.util.Map').implementation = function (s, i, m) {
            console.log("[getReportRaw] IN s=" + (s ? String(s).substring(0, 400) : "null") + " i=" + i + " map=" + mapStr(m));
            var r = this.getReportRaw(s, i, m);
            console.log("[getReportRaw] OUT " + mapStr(r));
            return r;
        };
        console.log("[getToken/getReportRaw] hooked");
    } catch (e) { console.log("[token/reportraw] fail: " + e); }
});

// ---- 5. native: libsscronet 0x4127ac 头构建 ----
function hookSscronet() {
    var base = Module.findBaseAddress("libsscronet.so");
    if (!base) { return false; }
    var target = base.add(0x4127ac);
    if (done.ssc) return true;
    try {
        Interceptor.attach(target, {
            onEnter: function (args) {
                this.x0 = args[0]; this.x1 = args[1];
                console.log("[sscronet:4127ac] ENTER x0=" + args[0] + " x1=" + args[1] + " x2=" + args[2]);
            },
            onLeave: function (retval) {
                console.log("[sscronet:4127ac] LEAVE ret=" + retval);
            }
        });
        done.ssc = true;
        console.log("[sscronet:4127ac] hooked base=" + base);
    } catch (e) { console.log("[sscronet] attach fail: " + e); }
    return true;
}

// ---- 6. native: libmetasec_ml JNI_OnLoad ----
function hookMetasec() {
    var base = Module.findBaseAddress("libmetasec_ml.so");
    if (!base) { return false; }
    if (done.ms) return true;
    try {
        Interceptor.attach(base.add(0x27e7f0), {
            onEnter: function (args) {
                console.log("[metasec] JNI_OnLoad vm=" + args[0]);
            }
        });
        done.ms = true;
        console.log("[metasec] JNI_OnLoad hooked base=" + base);
    } catch (e) { console.log("[metasec] attach fail: " + e); }
    return true;
}

var timer = setInterval(function () {
    hookSscronet();
    hookMetasec();
}, 200);

console.log("[dy_hook] loaded, waiting...");

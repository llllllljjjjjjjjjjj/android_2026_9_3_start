// 抖音 38.0.0 八神抓取 v7 (frida 16.5.7, ES5)
// 1. libart RegisterNatives: 抓 metasec 动态注册 native 表 → 函数偏移
// 2. SetHeader(37ed64): 签名头设置流
// 3. 4127ac onEnter: dump 头容器 (神头是否已写入? 判定写回路径)
// 4. 37f17c 序列化器: args[0..2] 三方向当 {ptr,len} 试

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

function readKV(p) {
    try {
        var ptr = p.readPointer();
        var len = p.add(8).readS64();
        if (len > 0 && len < 4096) return ptr.readUtf8String(len);
    } catch (e) { }
    return null;
}

var done = {};
var stats = { rn: 0, hdr4127: 0, ser: 0 };

// ---- 1. RegisterNatives ----
function hookRegisterNatives() {
    var art = Module.findBaseAddress("libart.so");
    if (!art || done.rn) return;
    done.rn = true;
    try {
        var rn = art.getExportByName("_ZN3art3JNI15RegisterNativesEP7_JNIEnvP7_jclassPK15JNINativeMethodi");
        if (!rn) { console.log("[RN] symbol not found"); return; }
        Interceptor.attach(rn, {
            onEnter: function (args) {
                var count = args[3].toInt32();
                var methods = args[2];
                var mb = Module.findBaseAddress("libmetasec_ml.so");
                var sb = Module.findBaseAddress("libsscronet.so");
                var anyMetasec = false;
                for (var i = 0; i < count; i++) {
                    try {
                        var np = methods.add(i * 24).readPointer();
                        var sp = methods.add(i * 24 + 8).readPointer();
                        var fp = methods.add(i * 24 + 16).readPointer();
                        var name = np.isNull() ? "?" : np.readUtf8String(200);
                        var sig = sp.isNull() ? "?" : sp.readUtf8String(200);
                        var off = "";
                        if (mb && fp.compare(mb) >= 0 && fp.sub(mb).toInt32() < 0x800000) { off = "meta+" + fp.sub(mb).toString(16); anyMetasec = true; }
                        else if (sb && fp.compare(sb) >= 0 && fp.sub(sb).toInt32() < 0x800000) { off = "sscro+" + fp.sub(sb).toString(16); anyMetasec = true; }
                        else { off = "" + fp; }
                        if (anyMetasec) console.log("[RN] " + name + " " + sig + " -> " + off);
                    } catch (e) { }
                }
                if (anyMetasec) console.log("[RN] count=" + count);
            }
        });
        console.log("[RN] RegisterNatives hooked");
    } catch (e) { console.log("[RN] fail: " + e); }
}

// ---- 2. SetHeader ----
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
                        console.log("[SETHDR] " + key + " => " + (val ? val.substring(0, 600) : "?"));
                    }
                } catch (e) { }
            }
        });
        console.log("[sethdr] hooked");
    } catch (e) { console.log("[sethdr] fail: " + e); }
}

// ---- 3. 4127ac onEnter: dump 头容器 ----
function hook4127() {
    var base = Module.findBaseAddress("libsscronet.so");
    if (!base || done.h4127) return;
    done.h4127 = true;
    try {
        Interceptor.attach(base.add(0x4127ac), {
            onEnter: function (args) {
                stats.hdr4127++;
                if (stats.hdr4127 % 30 !== 1) return;
                try {
                    // 容器 = [X19+8]+0x70 (4127ac x0 = URLRequest X19)
                    var p = args[0].add(8).readPointer();
                    if (p.isNull()) { console.log("[4127E] req+8 null"); return; }
                    var begin = p.add(0x70).readPointer();
                    var end = p.add(0x78).readPointer();
                    var diff = end.sub(begin);
                    if (diff.toInt32() >= 0 && diff.toInt32() <= 0x5000) {
                        var out = [], i = 0, q = begin;
                        while (q.compare(end) < 0 && i < 60) {
                            var name = readStdString(q);
                            var val = readStdString(q.add(0x18));
                            if (name) out.push(name + (isSigKey(name) ? "=" + (val ? val.substring(0, 300) : "?") : ""));
                            q = q.add(0x30); i++;
                        }
                        console.log("[4127E] container(" + diff + "): " + out.join(" | "));
                    }
                } catch (e) { console.log("[4127E] fail: " + e); }
            }
        });
        console.log("[4127ac] hooked");
    } catch (e) { console.log("[4127ac] fail: " + e); }
}

// ---- 4. 序列化器 37f17c 三方向 ----
function hookSer() {
    var base = Module.findBaseAddress("libsscronet.so");
    if (!base || done.ser) return;
    done.ser = true;
    try {
        Interceptor.attach(base.add(0x37f17c), {
            onEnter: function (args) {
                var n = (this.n || 0) + 1; this.n = n;
                if (n % 20 !== 1) return;
                var got = [];
                for (var a = 0; a < 3; a++) {
                    try {
                        var kv = readKV(args[a]);
                        if (kv && kv.length > 1) got.push("a" + a + "=" + kv.substring(0, 200));
                    } catch (e) { }
                }
                if (got.length) console.log("[SER] " + got.join(" || "));
            }
        });
        console.log("[ser] hooked");
    } catch (e) { console.log("[ser] fail: " + e); }
}

var timer = setInterval(function () {
    hookRegisterNatives();
    hookSet();
    hook4127();
    hookSer();
}, 150);
console.log("[dy_hook7] loaded");

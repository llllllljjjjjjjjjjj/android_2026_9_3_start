// 抖音 38.0.0 八神抓取 v8 (frida 16.5.7, ES5)
// v7 结论: 神头不走 SetHeader; 4127ac onEnter 容器只有 URL 无神头
// v8: 1) 修 RegisterNatives (Module.findExportByName)
//     2) 4127ac 打 LR (调用者=神头写回处)
//     3) 序列化器 37f17c 全量抓 "name: value" + LR
//     4) SetHeader 保留

var SIG_KEYS = ["x-argus", "x-gorgon", "x-ladon", "x-khronos", "x-helios", "x-medusa",
    "x-soter", "x-perseus", "x-tython", "x-ss-stub", "x-bogus"];

function isSigKey(k) {
    if (!k) return false;
    for (var i = 0; i < SIG_KEYS.length; i++) if (k === SIG_KEYS[i]) return true;
    return k.indexOf("x-metasec") === 0 || k.indexOf("x-") === 0;
}

function readKV(p) {
    try {
        var ptr = p.readPointer();
        var len = p.add(8).readS64();
        if (len > 0 && len < 4096) return ptr.readUtf8String(len);
    } catch (e) { }
    return null;
}

function readStdString(p) {
    try {
        var flag = p.add(0x17).readU8();
        if ((flag & 0x80) === 0) {
            if (flag > 0 && flag < 23) return p.readUtf8String(flag);
            return null;
        }
        var ptr = p.readPointer();
        var len = p.add(8).readS64();
        if (len > 0 && len < 4096) return ptr.readUtf8String(len);
    } catch (e) { }
    return null;
}

var done = {};
var cnt = { rn: 0, e4127: 0, l4127: 0, ser: 0 };

// ---- 1. RegisterNatives (libart 导出) ----
function hookRegisterNatives() {
    if (done.rn) return;
    done.rn = true;
    try {
        var rn = Module.findExportByName("libart.so", "_ZN3art3JNI15RegisterNativesEP7_JNIEnvP7_jclassPK15JNINativeMethodi");
        if (!rn) { console.log("[RN] export not found"); return; }
        Interceptor.attach(rn, {
            onEnter: function (args) {
                var count = args[3].toInt32();
                if (count <= 0 || count > 500) return;
                var methods = args[2];
                var mb = Module.findBaseAddress("libmetasec_ml.so");
                var sb = Module.findBaseAddress("libsscronet.so");
                var items = [];
                var relevant = false;
                for (var i = 0; i < count; i++) {
                    try {
                        var np = methods.add(i * 24).readPointer();
                        var sp = methods.add(i * 24 + 8).readPointer();
                        var fp = methods.add(i * 24 + 16).readPointer();
                        var name = np.isNull() ? "?" : np.readUtf8String(200);
                        var sig = sp.isNull() ? "?" : sp.readUtf8String(200);
                        var off = "";
                        if (mb && fp.compare(mb) >= 0 && fp.sub(mb).toInt32() < 0x900000) { off = "meta+" + fp.sub(mb).toString(16); relevant = true; }
                        else if (sb && fp.compare(sb) >= 0 && fp.sub(sb).toInt32() < 0x900000) { off = "sscro+" + fp.sub(sb).toString(16); relevant = true; }
                        if (relevant) items.push(name + sig + " -> " + off);
                    } catch (e) { }
                }
                if (relevant) {
                    console.log("[RN] " + items.join(" ;; "));
                    // 类名: 用 JNIEnv GetObjectClass 太绕, 通过 FindClass hook 关联
                }
            }
        });
        console.log("[RN] hooked");
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
                        var lr = this.returnAddress.sub(base).toString(16);
                        console.log("[SETHDR@+" + lr + "] " + key + " => " + (val ? val.substring(0, 400) : "?"));
                    }
                } catch (e) { }
            }
        });
        console.log("[sethdr] hooked");
    } catch (e) { console.log("[sethdr] fail: " + e); }
}

// ---- 3. 4127ac: LR + onEnter/onLeave 容器对比 ----
function hook4127() {
    var base = Module.findBaseAddress("libsscronet.so");
    if (!base || done.h4127) return;
    done.h4127 = true;
    try {
        Interceptor.attach(base.add(0x4127ac), {
            onEnter: function (args) {
                cnt.e4127++;
                this.lr = this.returnAddress.sub(base).toString(16);
                this.req = args[0];
            },
            onLeave: function (retval) {
                cnt.l4127++;
                if (cnt.l4127 % 20 !== 1) return;
                console.log("[4127ac] #" + cnt.l4127 + " caller=+" + this.lr);
                // onLeave 容器状态 (删除后)
                try {
                    var p = this.req.add(8).readPointer();
                    var begin = p.add(0x70).readPointer();
                    var end = p.add(0x78).readPointer();
                    var diff = end.sub(begin);
                    if (diff.toInt32() >= 0 && diff.toInt32() <= 0x5000) {
                        var out = [], i = 0, q = begin;
                        while (q.compare(end) < 0 && i < 30) {
                            var name = readStdString(q);
                            if (name) out.push(name.substring(0, 80));
                            q = q.add(0x30); i++;
                        }
                        console.log("[4127L] container(" + diff + "): " + out.join(" | "));
                    }
                } catch (e) { }
            }
        });
        console.log("[4127ac] hooked");
    } catch (e) { console.log("[4127ac] fail: " + e); }
}

// ---- 4. 序列化器 37f17c 全量 ----
function hookSer() {
    var base = Module.findBaseAddress("libsscronet.so");
    if (!base || done.ser) return;
    done.ser = true;
    try {
        Interceptor.attach(base.add(0x37f17c), {
            onEnter: function (args) {
                cnt.ser++;
                var got = [];
                for (var a = 0; a < 3; a++) {
                    try {
                        var kv = readKV(args[a]);
                        if (kv && kv.length > 1) got.push("a" + a + "=" + kv.substring(0, 120));
                    } catch (e) { }
                }
                if (got.length) {
                    var lr = this.returnAddress.sub(base).toString(16);
                    console.log("[SER@+" + lr + "] " + got.join(" || "));
                }
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
console.log("[dy_hook8] loaded");

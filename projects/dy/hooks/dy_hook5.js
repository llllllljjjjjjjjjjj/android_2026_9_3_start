// 抖音 38.0.0 八神签名抓取 v5 (frida 16.5.7, ES5)
// 核心: hook sub_37ED64 = SetHeader(obj, key{ptr,len}, value{ptr,len})
//      抓所有签名头(x-argus/x-gorgon/x-ladon/x-khronos...)的 key=>value 对拍
//      同时保留 Y2.a native 门 id 统计

var SIG_KEYS = ["x-argus", "x-gorgon", "x-ladon", "x-khronos", "x-helios", "x-medusa",
    "x-soter", "x-perseus", "x-tython", "x-ss-stub", "x-bogus", "x-bd-client-key",
    "x-ss-dp", "x-ss-req-ticket", "x-vc-bdturing", "x-tt-bypass-dp"];

function isSigKey(k) {
    if (!k) return false;
    for (var i = 0; i < SIG_KEYS.length; i++) if (k === SIG_KEYS[i]) return true;
    return k.indexOf("x-metasec") === 0;
}

function readKV(p) {
    // p 指向 {ptr,len}
    try {
        var ptr = p.readPointer();
        var len = p.add(8).readS64();
        if (len > 0 && len < 4096) return ptr.readUtf8String(len);
    } catch (e) { }
    return null;
}

var done = { core: false, set: 0, sig: 0 };

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
                            if (i !== 16777217 && i !== 33554445 && i !== 67108865) {
                                console.log("[Y2." + mn + "] id=" + i + " sub=" + i2 + " flag=" + j + " str=" + (s ? String(s).substring(0, 60) : "null"));
                            }
                            return r;
                        };
                })(mname);
            }
        }
    } catch (e) { console.log("[Y2] fail: " + e); }
});

function hookSetHeader() {
    var base = Module.findBaseAddress("libsscronet.so");
    if (!base) return;
    if (done.core) return;
    done.core = true;

    // sub_37ED64(obj, key{ptr,len}, value{ptr,len})
    Interceptor.attach(base.add(0x37ed64), {
        onEnter: function (args) {
            done.set++;
            var key = readKV(args[1]);
            if (!key || !isSigKey(key)) return;
            var val = readKV(args[2]);
            var lr = this.returnAddress.sub(base).toString(16);
            done.sig++;
            console.log("[SETHDR@+" + lr + " #" + done.sig + "] " + key + " => " + (val ? val.substring(0, 600) : "?"));
            if (done.sig % 30 === 1) console.log("[SETHDR] setTotal=" + done.set + " sigTotal=" + done.sig);
        }
    });
    console.log("[sethdr:37ed64] hooked");
}

var timer = setInterval(function () { hookSetHeader(); }, 150);
console.log("[dy_hook5] loaded");

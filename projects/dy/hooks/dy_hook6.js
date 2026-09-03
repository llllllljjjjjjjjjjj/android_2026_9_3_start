// 抖音 38.0.0 八神签名抓取 v6 (frida 16.5.7, ES5)
// 1. hook 0x37f17c (HTTP 头序列化器): dump 完整请求头集合 → 找神头
// 2. hook sub_37ED64 SetHeader (v5 验证过可用)
// 3. 两个 hook 都扫请求对象找 URL 关联

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

var done = { ser: 0, set: 0 };

function hookSer() {
    var base = Module.findBaseAddress("libsscronet.so");
    if (!base || done.ser) return;
    done.ser = true;
    // 0x37f17c: 序列化头容器 (元素 0x30 = {name,value} std::string 对)
    Interceptor.attach(base.add(0x37f17c), {
        onEnter: function (args) {
            var n = (this.n || 0) + 1; this.n = n;
            if (n % 50 !== 1) return;   // 采样
            // args[0] 当容器 (begin/end) 试
            try {
                var begin = args[0].readPointer();
                var end = args[0].add(8).readPointer();
                var diff = end.sub(begin);
                if (diff.toInt32() >= 0 && diff.toInt32() <= 0x3000) {
                    var out = [];
                    var p = begin, i = 0;
                    while (p.compare(end) < 0 && i < 40) {
                        var name = readStdString(p);
                        var val = readStdString(p.add(0x18));
                        if (name) out.push(name + "=" + (val ? val.substring(0, 300) : "?"));
                        p = p.add(0x30); i++;
                    }
                    console.log("[SER0] " + out.join(" | "));
                }
            } catch (e) { }
            // args[1] 当 {ptr,len} 试
            try {
                var kv = readKV(args[1]);
                if (kv) console.log("[SER1] " + kv.substring(0, 300));
            } catch (e) { }
        }
    });
    console.log("[ser:37f17c] hooked");
}

function hookSet() {
    var base = Module.findBaseAddress("libsscronet.so");
    if (!base || done.set) return;
    done.set = true;
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
    console.log("[sethdr:37ed64] hooked");
}

var timer = setInterval(function () { hookSer(); hookSet(); }, 150);
console.log("[dy_hook6] loaded");

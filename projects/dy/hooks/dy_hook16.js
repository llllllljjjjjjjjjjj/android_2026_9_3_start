// 抖音 38.0.0 八神抓取 v16 (frida 16.5.7, ES5, attach 模式)
// 沿 sub_47A31C 内部桥接抓 metasec 回调明文:
//   1) qword_5FFE80 全局回调指针 → 定位模块 (预期 libmetasec_ml.so)
//   2) 47aaec BLR X23: 入参 (url?, headers 拼接串) + 返回 (签名头串)
//   3) sub_37ED64 SetHeader: 过滤八神 name=value (写入瞬间)
//   4) 47B598/47B740/47BA98 计数 + 412680 容器验证 + 心跳

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

function readMaybeStr(p) {
    if (p.isNull()) return null;
    try {
        var s = p.readUtf8String(400);
        if (s && s.length > 0 && s.length < 400) return s;
    } catch (e) { }
    return readStdString(p);
}

function isGod(name) {
    var n = name.toLowerCase();
    var GOD = ["x-argus", "x-gorgon", "x-ladon", "x-khronos", "x-helios",
               "x-medusa", "x-soter", "x-perseus", "x-tython", "x-bogus", "x-ss-stub"];
    for (var i = 0; i < GOD.length; i++) if (n.indexOf(GOD[i]) === 0) return true;
    return false;
}

function godHeaders(ptr) {
    try {
        var begin = ptr.readPointer();
        var end = ptr.add(8).readPointer();
        var diff = end.sub(begin);
        if (diff.toInt32() < 0 || diff.toInt32() > 0x6000) return "(bad)";
        var out = [], i = 0, q = begin;
        while (q.compare(end) < 0 && i < 40) {
            var name = readStdString(q);
            if (name && isGod(name)) {
                var val = readStdString(q.add(0x18));
                out.push(name + "=" + (val ? val.substring(0, 60) : "?"));
            }
            q = q.add(0x30); i++;
        }
        return out.length ? out.join(" ") : "(no-gods)";
    } catch (e) { return "ERR:" + e; }
}

var base = Module.findBaseAddress("libsscronet.so");
console.log("[base] libsscronet = " + base);

var cnt = { a31c: 0, blr: 0, sh: 0, shgod: 0, b598: 0, b740: 0, ba98: 0, e680: 0 };
var ptrDone = false;

// 1) 47A31C 入口: 读 qword_5FFE80 全局回调指针
try {
    Interceptor.attach(base.add(0x47a31c), {
        onEnter: function (args) {
            cnt.a31c++;
            if (!ptrDone) {
                ptrDone = true;
                try {
                    var fp = base.add(0x5FFE80).readPointer();
                    var m = Process.findModuleByAddress(fp);
                    var loc = m ? m.name + "+" + fp.sub(m.base).toString(16) : String(fp);
                    console.log("[PTR5FFE80] " + fp + " => " + loc);
                } catch (e) { console.log("[PTR5FFE80] ERR " + e); }
            }
        }
    });
    console.log("[47a31c] hooked");
} catch (e) { console.log("[47a31c] fail: " + e); }

// 2) 47aaec BLR X23: metasec 回调调用点
try {
    Interceptor.attach(base.add(0x47aaec), {
        onEnter: function (args) {
            cnt.blr++;
            if (cnt.blr <= 10) {
                var a = readMaybeStr(args[0]);
                var b = readMaybeStr(args[1]);
                console.log("[BLR-IN] #" + cnt.blr +
                    " X0=" + (a ? a.substring(0, 300) : "?") +
                    " X1=" + (b ? b.substring(0, 300) : "?"));
            }
        },
        onLeave: function (retval) {
            if (cnt.blr <= 10) {
                var r = readMaybeStr(retval);
                console.log("[BLR-OUT] #" + cnt.blr + " ret=" + (r ? r.substring(0, 600) : "null"));
            }
        }
    });
    console.log("[47aaec BLR] hooked");
} catch (e) { console.log("[47aaec] fail: " + e); }

// 3) SetHeader 37ED64: 写入瞬间抓八神名值对
try {
    Interceptor.attach(base.add(0x37ed64), {
        onEnter: function (args) {
            cnt.sh++;
            var name = readStdString(args[1]);
            if (name && isGod(name)) {
                cnt.shgod++;
                var val = readStdString(args[2]);
                console.log("[SET-GOD] #" + cnt.shgod + " " + name + "=" + (val ? val.substring(0, 120) : "?"));
            }
        }
    });
    console.log("[37ed64 SetHeader] hooked");
} catch (e) { console.log("[37ed64] fail: " + e); }

// 4) 47B598/47B740/47BA98 计数
try { Interceptor.attach(base.add(0x47b598), { onEnter: function () { cnt.b598++; if (cnt.b598 <= 5) console.log("[47B598] #" + cnt.b598); } }); console.log("[47b598] hooked"); } catch (e) { console.log("[47b598] fail: " + e); }
try { Interceptor.attach(base.add(0x47b740), { onEnter: function () { cnt.b740++; if (cnt.b740 <= 5) console.log("[47B740] #" + cnt.b740); } }); console.log("[47b740] hooked"); } catch (e) { console.log("[47b740] fail: " + e); }
try { Interceptor.attach(base.add(0x47ba98), { onEnter: function () { cnt.ba98++; if (cnt.ba98 <= 5) console.log("[47BA98] #" + cnt.ba98); } }); console.log("[47ba98] hooked"); } catch (e) { console.log("[47ba98] fail: " + e); }

// 5) 412680 容器验证 (前 3 次)
try {
    Interceptor.attach(base.add(0x412680), {
        onEnter: function (args) {
            cnt.e680++;
            if (cnt.e680 <= 3) {
                console.log("[412680-E] #" + cnt.e680 + " hdr: " + godHeaders(args[0].add(0x358)));
            }
        }
    });
    console.log("[412680] hooked");
} catch (e) { console.log("[412680] fail: " + e); }

// 6) 心跳
setInterval(function () {
    console.log("[beat] a31c=" + cnt.a31c + " blr=" + cnt.blr + " sh=" + cnt.sh + " shgod=" + cnt.shgod +
        " b598=" + cnt.b598 + " b740=" + cnt.b740 + " ba98=" + cnt.ba98 + " e680=" + cnt.e680);
}, 15000);

console.log("[dy_hook16] loaded");

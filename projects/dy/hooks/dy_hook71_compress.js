// dy_hook71_compress.js — hook Java 层 zstd 压缩，抓 body 明文
Java.perform(function () {
  ["com.bytedance.compression.zstd.ZstdCompress",
   "com.bytedance.compression.zstd.ZstdCompressCtx"].forEach(function (cn) {
    try {
      var C = Java.use(cn);
      var ms = C.class.getDeclaredMethods();
      ms.forEach(function (m) {
        var name = m.getName();
        // 压缩方法
        if (/compress/.test(name)) {
          try {
            C[name].overloads.forEach(function (ov) {
              var sig = ov.argumentTypes.map(function (t) { return t.className; }).join(",");
              if (sig.indexOf("[B") !== 0 && sig.indexOf("byte") !== 0) return;
              ov.implementation = function () {
                var a = arguments;
                // 找 byte[] 参数（输入 form 明文）
                for (var i = 0; i < a.length; i++) {
                  try {
                    if (a[i] && a[i].$className === "[B" && a[i].length > 100) {
                      var bytes = Java.array("byte", a[i]);
                      var s = "";
                      for (var j = 0; j < Math.min(400, bytes.length); j++) s += String.fromCharCode(bytes[j] & 0xff);
                      if (/keyword|search/.test(s)) {
                        console.log("[COMPRESS] " + cn + "." + name + "(" + sig + ") input len=" + a[i].length);
                        console.log("[COMPRESS]   form明文: " + s.slice(0, 300));
                      }
                    }
                  } catch (e) {}
                }
                var r = ov.apply(this, arguments);
                return r;
              };
            });
          } catch (e) {}
        }
      });
      console.log("[hook71] " + cn + " 方法枚举完成");
    } catch (e) { console.log("[hook71] " + cn + " fail: " + e); }
  });
});
console.log("[hook71] loaded");

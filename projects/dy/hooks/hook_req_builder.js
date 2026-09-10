"use strict";
// 定位 client.Request 的 header 注入：枚举 Builder 方法 + hook build()
Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }
  var B;
  try {
    B = Java.use("com.bytedance.retrofit2.client.Request$Builder");
    var ms = B.class.getDeclaredMethods();
    console.log("@@ BM count=" + ms.length);
    ms.forEach(function (m) {
      console.log("@@ BM " + m.getName() + "(" + m.getParameterTypes().map(function (t) { return t.getName().split(".").pop(); }).join(",") + ")");
    });
  } catch (e) { console.log("@@ builder err " + S(e)); return; }

  if (B.build) {
    B.build.overloads.forEach(function (o) {
      o.implementation = function () {
        var r = o.call(this, Array.prototype.slice.call(arguments));
        try {
          var hs = r.getHeaders();
          var n = hs ? hs.size() : -1;
          if (n > 0) {
            var out = ["@@ BUILT headers=" + n];
            try {
              var JO = Java.use("org.json.JSONObject");
              // 手工取 header 列表
              for (var i = 0; i < n && i < 40; i++) {
                var h = hs.get(i);
                try { out.push("@@   " + S(h.getName()) + ": " + S(h.getValue()).slice(0, 80)); } catch (e2) { out.push("@@   <unreadable>"); }
              }
            } catch (e3) { }
            console.log(out.join("\n"));
          }
        } catch (e) { }
        return r;
      };
    });
    console.log("@@ hooked client.Request$Builder.build");
  }
});

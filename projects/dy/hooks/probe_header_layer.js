"use strict";
// 探测：最终请求头在哪一层注入（okhttp3 是否参与 / cronet 层）
Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }

  // 1) okhttp3.Request$Builder.addHeader 是否被调用
  try {
    var OB = Java.use("okhttp3.Request$Builder");
    OB.addHeader.implementation = function (n, v) {
      console.log("[okhttp addHeader] " + S(n) + ": " + S(v).slice(0, 60));
      return this.addHeader(n, v);
    };
    console.log("[*] hooked okhttp3.Request$Builder.addHeader");
  } catch (e) { console.log("okhttp hook err " + S(e)); }

  // 2) okhttp3.Request 构造（最终请求对象）
  try {
    var RQ = Java.use("okhttp3.Request");
    var ctors = RQ.$init.overloads;
    ctors.forEach(function (c) {
      c.implementation = function () {
        var r = c.call(this, Array.prototype.slice.call(arguments));
        try {
          console.log("[okhttp Request] " + S(r.method()) + " " + S(r.url().toString()).slice(0, 120));
        } catch (e2) {}
        return r;
      };
    });
    console.log("[*] hooked okhttp3.Request ctors (" + ctors.length + ")");
  } catch (e) { console.log("okhttp Request hook err " + S(e)); }

  // 3) cronet 请求入口
  try {
    var CC = Java.use("com.bytedance.frameworks.baselib.network.http.cronet.ICronetClient");
    var ms = CC.class.getDeclaredMethods();
    console.log("=== ICronetClient methods (" + ms.length + ") ===");
    ms.forEach(function (m) {
      var ps = m.getParameterTypes().map(function (t) { return t.getName(); }).join(",");
      console.log("  " + m.getName() + "(" + ps.slice(0, 100) + ")");
    });
  } catch (e) { console.log("cronet enum err " + S(e)); }
});

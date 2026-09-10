"use strict";
// dy 可读抓包 v3：枚举 bitly client.Request 方法 + 从 build 结果 dump 完整请求
Java.perform(function () {
  try {
    var RQ = Java.use("com.bytedance.retrofit2.client.Request");
    var ms = RQ.class.getDeclaredMethods();
    console.log("=== client.Request methods (" + ms.length + ") ===");
    ms.forEach(function (m) {
      var ps = m.getParameterTypes().map(function (t) { return t.getName(); }).join(",");
      console.log("  R." + m.getName() + "(" + ps + ") -> " + m.getReturnType().getName());
    });
  } catch (e) { console.log("enum err " + e); }
});

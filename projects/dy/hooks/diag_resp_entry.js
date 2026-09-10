"use strict";
// 诊断：响应解析入口候选类
Java.perform(function () {
  function dump(cn, max) {
    try {
      var C = Java.use(cn);
      var ms = C.class.getDeclaredMethods();
      console.log("=== " + cn + " (" + ms.length + ") ===");
      ms.slice(0, max || 25).forEach(function (m) {
        var ps = m.getParameterTypes().map(function (t) { return t.getName().split(".").pop(); }).join(",");
        console.log("  " + m.getName() + "(" + ps + ") -> " + m.getReturnType().getName().split(".").pop());
      });
    } catch (e) { console.log(cn + " ABSENT/err"); }
  }
  dump("com.bytedance.aweme.coffee.json.JSONTokenerGetter", 20);
  dump("com.bytedance.retrofit2.mime.TypedByteArray", 20);
  dump("com.bytedance.retrofit2.Converter", 15);
  dump("com.bytedance.retrofit2.RetrofitMetrics", 20);
  try {
    var RB = Java.use("com.bytedance.retrofit2.RequestBuilder");
    console.log("RBCheck ok");
  } catch (e) {}
});

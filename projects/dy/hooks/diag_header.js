"use strict";
Java.perform(function () {
  ["com.bytedance.retrofit2.client.Header"].forEach(function (cn) {
    try {
      var C = Java.use(cn);
      var ms = C.class.getDeclaredMethods();
      console.log("=== " + cn + " (" + ms.length + ") ===");
      ms.forEach(function (m) {
        var ps = m.getParameterTypes().map(function (t) { return t.getName(); }).join(",");
        console.log("  " + m.getName() + "(" + ps + ") -> " + m.getReturnType().getName());
      });
      var fs = C.class.getDeclaredFields();
      fs.forEach(function (f) { console.log("  FIELD " + f.getName() + " : " + f.getType().getName()); });
    } catch (e) { console.log(cn + " err " + e); }
  });
});

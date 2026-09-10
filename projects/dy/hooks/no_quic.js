"use strict";
// 尝试禁用 QUIC: hook CronetEngine.Builder.enableQuic
Java.perform(function () {
  function tryHook(cls, method) {
    try {
      var C = Java.use(cls);
      var m = C[method].overload("boolean");
      m.implementation = function (v) {
        if (v) { console.log("@@ no-quic: force disable QUIC"); }
        return m.call(this, false);
      };
      console.log("@@ hooked " + cls + "." + method);
    } catch (e) { }
  }
  ["org.chromium.net.CronetEngine$Builder",
   "com.bytedance.ttnet.TTNetInit$Builder",
   "org.chromium.net.CronetBuilder"].forEach(function (c) {
    tryHook(c, "enableQuic");
  });
  // 备选: hook 网络库 QUIC 开关字段
  try {
    var SS = Java.use("com.bytedance.frameworks.baselib.network.http.cronet.TTNetModule");
    console.log("@@ TTNetModule found");
  } catch (e) { }
});

"use strict";
// dy 可读抓包：枚举 byte-retrofit RequestBuilder 方法 + hook okhttp Request 构造
Java.perform(function () {
  function log(s) { console.log(s); }

  // 1. 枚举 RequestBuilder 方法签名（确认 hook 点）
  try {
    var RB = Java.use("com.bytedance.retrofit2.RequestBuilder");
    var ms = RB.class.getDeclaredMethods();
    log("=== RequestBuilder methods (" + ms.length + ") ===");
    ms.forEach(function (m) {
      log("  RB." + m.getName() + " -> " + m.getReturnType().getName());
    });
  } catch (e) { log("RB enum err " + e); }

  // 2. 枚举 okhttp3.Request.Builder 方法
  try {
    var OB = Java.use("okhttp3.Request$Builder");
    var ms2 = OB.class.getDeclaredMethods();
    log("=== okhttp Request$Builder methods (" + ms2.length + ") ===");
    ms2.forEach(function (m) {
      log("  OB." + m.getName() + " -> " + m.getReturnType().getName());
    });
  } catch (e) { log("OB enum err " + e); }

  // 3. 枚举 okhttp3.Request 方法（含 headers/url/method）
  try {
    var RQ = Java.use("okhttp3.Request");
    var ms3 = RQ.class.getDeclaredMethods();
    log("=== okhttp Request methods (" + ms3.length + ") ===");
    ms3.forEach(function (m) {
      log("  RQ." + m.getName() + " -> " + m.getReturnType().getName());
    });
  } catch (e) { log("RQ enum err " + e); }
});

"use strict";
// 安全 hook: TTNet 请求日志（低频，每请求一次，不在热路径）
Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }
  var n = 0;
  try {
    var M = Java.use("com.bytedance.retrofit2.RetrofitMetrics");
    if (M.generateTTNetLog) {
      M.generateTTNetLog.implementation = function (jo) {
        try {
          var txt = String(jo.toString());
          if (/search|x-tt-token|x-bd-client-key/i.test(txt)) {
            n++;
            console.log("@@LOG[" + n + "] len=" + txt.length);
            console.log("@@LOGTXT " + txt.slice(0, 5000));
          }
        } catch (e) { }
        return this.generateTTNetLog(jo);
      };
      console.log("@@ hooked generateTTNetLog");
    }
  } catch (e) { console.log("@@ metrics hook err " + S(e)); }
});

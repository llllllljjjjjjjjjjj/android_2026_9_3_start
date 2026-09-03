// dy_hook67_bt3.js — org.json 解析搜索响应时 dump native backtrace（定位解压函数）
Java.perform(function () {
  ["org.json.JSONObject", "org.json.JSONTokener"].forEach(function (cn) {
    try {
      var C = Java.use(cn);
      C.$init.overloads.forEach(function (ov) {
        if (ov.argumentTypes.map(function (t) { return t.className; }).join(",") === "java.lang.String") {
          ov.implementation = function (s) {
            var str = String(s);
            if (str.length > 100 && /search_result_id|aweme_id/.test(str)) {
              var bt = Thread.backtrace(this.context || null, Backtracer.ACCURATE);
              console.log("[NATIVE-BT] ========== 搜索响应解析 ==========");
              console.log("[NATIVE-BT] head=" + str.slice(0, 60));
              for (var i = 0; i < Math.min(bt.length, 25); i++) {
                var a = bt[i];
                var m = Process.findModuleByAddress(a);
                if (m) console.log("[NATIVE-BT]   " + m.name + "+0x" + a.sub(m.base).toString(16));
                else console.log("[NATIVE-BT]   " + a);
              }
            }
            return ov.call(this, s);
          };
        }
      });
    } catch (e) {}
  });
});
console.log("[hook67] loaded");

// dy_hook59_bt2.js — org.json 解析搜索响应时 dump Java 调用栈（定位解压函数）
Java.perform(function () {
  var C = Java.use("org.json.JSONObject");
  C.$init.overloads.forEach(function (ov) {
    if (ov.argumentTypes.map(function (t) { return t.className; }).join(",") === "java.lang.String") {
      ov.implementation = function (s) {
        var str = String(s);
        if (str.length > 100 && /search_result_id|aweme_id|"desc"|business_data/.test(str)) {
          var ex = Java.use("java.lang.Exception").$new("bt");
          var st = ex.getStackTrace();
          var frames = [];
          for (var i = 0; i < st.length && i < 30; i++) frames.push(st[i].toString());
          console.log("[JSON-BT] ========== 搜索响应 JSON 解析 ==========");
          console.log("[JSON-BT] head=" + str.slice(0, 80));
          console.log("[JSON-BT] " + frames.join("\n[JSON-BT] "));
        }
        return ov.call(this, s);
      };
    }
  });
});
console.log("[hook59] loaded");

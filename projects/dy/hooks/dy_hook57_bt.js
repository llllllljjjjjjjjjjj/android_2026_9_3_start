// dy_hook57_bt.js — hook org.json.JSONObject 解析，dump native backtrace 定位解压调用链
Java.perform(function () {
  var C = Java.use("org.json.JSONObject");
  C.$init.overload("java.lang.String").implementation = function (s) {
    var str = String(s);
    if (/aweme_id|search_result_id|business_data/.test(str)) {
      // 打印 native backtrace
      var bt = Thread.backtrace(this.$handle ? null : null, Backtracer.ACCURATE);
      // 上面写法不稳，改用 Java 栈 + native 栈
      var log = Java.use("android.util.Log");
      var ex = Java.use("java.lang.Exception");
      var e = ex.$new("bt");
      var st = e.getStackTrace();
      var frames = [];
      for (var i = 0; i < st.length && i < 25; i++) frames.push(st[i].toString());
      console.log("[JSON-BT] ============ 搜索响应 JSON 解析调用栈 ============");
      console.log("[JSON-BT] " + frames.join("\n[JSON-BT] "));
    }
    return this.$init(s);
  };
});
console.log("[hook57] loaded");

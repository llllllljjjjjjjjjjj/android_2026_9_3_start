// dy_hook42_json_all.js — 全量 JSON 解析探针（顶层定位响应解析路径）
// 无过滤：所有 >300 字符的 JSON 构造都打头 120 字符，看 search 响应从哪过
Java.perform(function () {
  var targets = [
    "org.json.JSONObject",
    "org.json.JSONTokener",
    "com.bytedance.mt.protocol.impl.json.JSONObject",
    "com.alibaba.fastjson.JSONObject",
    "com.google.gson.JsonParser"
  ];
  targets.forEach(function (clsName) {
    try {
      var C = Java.use(clsName);
      var n = 0;
      C.$init.overloads.forEach(function (ov) {
        var at = ov.argumentTypes.map(function (t) { return t.className; }).join(",");
        if (at === "java.lang.String" || at === "java.io.Reader") {
          ov.implementation = function (arg) {
            try {
              var s = String(arg);
              if (s.length > 300) {
                send({ t: "j", cls: clsName, at: at, len: s.length,
                       head: s.slice(0, 120).replace(/\n/g, " ") });
              }
            } catch (e) {}
            return ov.call(this, arg);
          };
          n++;
        }
      });
      console.log("[hook] " + clsName + " ctors=" + n);
    } catch (e) {
      // 类未加载
    }
  });
});

// dy_hook43_json_reader.js — 补 Reader 路径 + 过滤 business_data/search 响应特征
Java.perform(function () {
  var cands = ["org.json.JSONTokener", "org.json.JSONObject"];
  cands.forEach(function (clsName) {
    try {
      var C = Java.use(clsName);
      C.$init.overloads.forEach(function (ov) {
        var at = ov.argumentTypes.map(function (t) { return t.className; }).join(",");
        if (at === "java.io.Reader") {
          ov.implementation = function (rd) {
            try {
              var s = String(rd);
              send({ t: "r", cls: clsName, len: s.length, head: s.slice(0, 100).replace(/\n/g, " ") });
            } catch (e) {}
            return ov.call(this, rd);
          };
          console.log("[hook] " + clsName + "(Reader)");
        }
      });
    } catch (e) {}
  });
  // 顺带过滤 String 路径里的 business_data（补全）
  try {
    var T = Java.use("org.json.JSONTokener");
    T.$init.overloads.forEach(function (ov) {
      var at = ov.argumentTypes.map(function (t) { return t.className; }).join(",");
      if (at === "java.lang.String") {
        ov.implementation = function (str) {
          var s = String(str);
          if (/business_data|"aweme_info"|search_result/.test(s)) {
            send({ t: "hit", len: s.length, head: s.slice(0, 300).replace(/\n/g, " ") });
          }
          return ov.call(this, str);
        };
        console.log("[hook] JSONTokener(String) filtered");
      }
    });
  } catch (e) {}
});

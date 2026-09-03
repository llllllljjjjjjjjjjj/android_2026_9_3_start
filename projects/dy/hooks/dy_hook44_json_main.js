// dy_hook44_json_main.js — 主响应捕获：JSONObject/JSONTokener 全入口 + 大 JSON/特征过滤
Java.perform(function () {
  function hookCtor(clsName, filter) {
    try {
      var C = Java.use(clsName);
      C.$init.overloads.forEach(function (ov) {
        var at = ov.argumentTypes.map(function (t) { return t.className; }).join(",");
        if (at === "java.lang.String") {
          ov.implementation = function (str) {
            try {
              var s = String(str);
              if (filter(s)) send({ t: "big", cls: clsName, len: s.length, body: s.slice(0, 4000) });
            } catch (e) {}
            return ov.call(this, str);
          };
          console.log("[hook] " + clsName + "(String)");
        }
      });
    } catch (e) { console.log("[skip] " + clsName + ": " + e.message); }
  }

  function big(s) {
    return (s.length > 8000 && /search|aweme|general/i.test(s)) ||
           /business_data|"aweme_list"|"aweme_info"/.test(s);
  }
  function bigTok(s) {
    return (s.length > 8000 && /search|aweme|general/i.test(s)) ||
           /business_data|"aweme_list"|"aweme_info"/.test(s);
  }
  hookCtor("org.json.JSONObject", big);
  hookCtor("org.json.JSONTokener", bigTok);
});

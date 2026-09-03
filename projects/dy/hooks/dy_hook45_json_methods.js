// dy_hook45_json_methods.js — 补 JSON 解析方法层（fastjson/Gson/org.json parse）
Java.perform(function () {
  function keep(s) {
    return (/search_keyword|search_result_id|business_data|"aweme_info"|general_search/.test(s) &&
            s.length > 200 && s.length < 300000) ||
           (s.length > 10000 && /"aweme"|"data"/.test(s) && /search/.test(s));
  }
  function report(cls, m, s) {
    try { send({ t: "j", cls: cls, m: m, len: s.length, body: s.slice(0, 200000) }); } catch (e) {}
  }

  // fastjson 静态 parseObject/parse
  try {
    var FJ = Java.use("com.alibaba.fastjson.JSON");
    FJ.parseObject.overloads.forEach(function (ov) {
      var at = ov.argumentTypes.map(function (t) { return t.className; }).join(",");
      if (at.indexOf("java.lang.String") === 0) {
        ov.implementation = function (s) {
          try { if (keep(String(s))) report("fastjson", "parseObject", String(s)); } catch (e) {}
          return ov.call(this, s);
        };
        console.log("[hook] fastjson.JSON.parseObject(" + at + ")");
      }
    });
    FJ.parse.overloads.forEach(function (ov) {
      var at = ov.argumentTypes.map(function (t) { return t.className; }).join(",");
      if (at.indexOf("java.lang.String") === 0) {
        ov.implementation = function (s) {
          try { if (keep(String(s))) report("fastjson", "parse", String(s)); } catch (e) {}
          return ov.call(this, s);
        };
        console.log("[hook] fastjson.JSON.parse(" + at + ")");
      }
    });
  } catch (e) { console.log("[skip] fastjson: " + e.message); }

  // gson fromJson(String, ...)
  try {
    var G = Java.use("com.google.gson.Gson");
    G.fromJson.overloads.forEach(function (ov) {
      var at = ov.argumentTypes.map(function (t) { return t.className; }).join(",");
      if (at.indexOf("java.lang.String") === 0) {
        ov.implementation = function (s) {
          try { if (keep(String(s))) report("gson", "fromJson", String(s)); } catch (e) {}
          return ov.call(this, s);
        };
        console.log("[hook] gson.Gson.fromJson(" + at + ")");
      }
    });
  } catch (e) { console.log("[skip] gson: " + e.message); }
});

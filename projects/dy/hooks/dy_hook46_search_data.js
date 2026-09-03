// dy_hook46_search_data.js — 合并顶层 hook：JSON 构造+解析方法 → 搜索完整数据
// 覆盖: org.json.JSONObject/JSONTokener(String) + fastjson parseObject/parse + gson fromJson(String)
Java.perform(function () {
  function keep(s) {
    return (/search_keyword|search_result_id|business_data|"aweme_info"|general_search|"data"|"render_info"/.test(s) &&
            s.length > 200 && s.length < 400000);
  }
  function rep(cls, m, s) {
    try { send({ t: "j", cls: cls, m: m, len: s.length, body: s }); } catch (e) {}
  }

  // org.json ctors
  ["org.json.JSONObject", "org.json.JSONTokener"].forEach(function (cn) {
    try {
      var C = Java.use(cn);
      C.$init.overloads.forEach(function (ov) {
        if (ov.argumentTypes.map(function (t) { return t.className; }).join(",") === "java.lang.String") {
          ov.implementation = function (s) {
            try { if (keep(String(s))) rep(cn, "$init", String(s)); } catch (e) {}
            return ov.call(this, s);
          };
        }
      });
      console.log("[hook] " + cn);
    } catch (e) { console.log("[skip] " + cn); }
  });

  // fastjson
  try {
    var FJ = Java.use("com.alibaba.fastjson.JSON");
    FJ.parseObject.overloads.forEach(function (ov) {
      var at = ov.argumentTypes.map(function (t) { return t.className; }).join(",");
      if (at.indexOf("java.lang.String") === 0) {
        ov.implementation = function (s) {
          try { if (keep(String(s))) rep("fastjson", "parseObject", String(s)); } catch (e) {}
          return ov.call(this, s);
        };
        console.log("[hook] fastjson.parseObject");
      }
    });
    FJ.parse.overloads.forEach(function (ov) {
      var at = ov.argumentTypes.map(function (t) { return t.className; }).join(",");
      if (at.indexOf("java.lang.String") === 0) {
        ov.implementation = function (s) {
          try { if (keep(String(s))) rep("fastjson", "parse", String(s)); } catch (e) {}
          return ov.call(this, s);
        };
        console.log("[hook] fastjson.parse");
      }
    });
  } catch (e) { console.log("[skip] fastjson"); }

  // gson
  try {
    var G = Java.use("com.google.gson.Gson");
    G.fromJson.overloads.forEach(function (ov) {
      var at = ov.argumentTypes.map(function (t) { return t.className; }).join(",");
      if (at.indexOf("java.lang.String") === 0) {
        ov.implementation = function (s) {
          try { if (keep(String(s))) rep("gson", "fromJson", String(s)); } catch (e) {}
          return ov.call(this, s);
        };
        console.log("[hook] gson.fromJson");
      }
    });
  } catch (e) { console.log("[skip] gson"); }
});

"use strict";
// Gson 全量捕获：String 版 + JsonReader 版（流式），完整落盘大 JSON
var n = 0;

Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }

  function mark(json, clsName, via) {
    try {
      if (!json) return;
      var hit = (clsName && /Search|SearchMixFeed|Aweme/i.test(clsName))
        || /"aweme_list"|"aweme_id"|"card_name"|"doc_dict"/.test(json);
      if (!hit) return;
      n++;
      console.log("@@GSON[" + n + "] via=" + via + " cls=" + clsName + " len=" + json.length);
      console.log("@@GSONJSON " + json.slice(0, 8000));
    } catch (e) { }
  }

  var Gson = Java.use("com.google.gson.Gson");

  // 1) String 版
  [["java.lang.String", "java.lang.Class"],
   ["java.lang.String", "java.lang.reflect.Type"]].forEach(function (sig) {
    try {
      var o = Gson.fromJson.overload.apply(Gson.fromJson, sig);
      o.implementation = function () {
        var args = Array.prototype.slice.call(arguments);
        var r = o.apply(this, args);
        try {
          var clsName = "";
          try { clsName = args[1] ? S(args[1].getName()) : ""; } catch (e1) { clsName = S(args[1]); }
          if (typeof args[0] === "string") mark(args[0], clsName, "String");
        } catch (e) { }
        return r;
      };
    } catch (e) { console.log("@@ str sig err " + S(e)); }
  });

  // 2) JsonReader 版（流式解析，拿不到源串 → 记录类型名）
  try {
    var o2 = Gson.fromJson.overload("com.google.gson.stream.JsonReader", "java.lang.reflect.Type");
    o2.implementation = function () {
      var args = Array.prototype.slice.call(arguments);
      var cn = "";
      try { cn = S(args[1]) ; } catch (e) { }
      if (/Search|Aweme/i.test(cn)) {
        console.log("@@GSONREADER cls=" + cn);
      }
      return o2.apply(this, args);
    };
    console.log("@@ hooked fromJson(JsonReader,Type)");
  } catch (e) { console.log("@@ reader sig err " + S(e)); }

  console.log("@@ gson hook ready");
});

"use strict";
// 视频详情 playCount：低侵入方案 —— hook Gson 解析，过滤含 play_count 的响应
var seen = {};
var out = [];
var n = 0;

Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return null; } }

  function parse(json) {
    try {
      if (!json || json.indexOf("play_count") < 0) return;
      // 提取 aid / play_count / digg_count / desc
      var aid = (json.match(/"aweme_id"\s*:\s*"(\d+)"/) || [])[1]
        || (json.match(/"aid"\s*:\s*"(\d+)"/) || [])[1];
      var play = (json.match(/"play_count"\s*:\s*(\d+)/) || [])[1];
      var digg = (json.match(/"digg_count"\s*:\s*(\d+)/) || [])[1];
      var desc = (json.match(/"desc"\s*:\s*"([^"]{0,120})/) || [])[1];
      if (!aid) return;
      var key = aid + "|" + play;
      if (seen[key]) return;
      seen[key] = 1;
      n++;
      var rec = { aid: aid, play: play, digg: digg, desc: desc };
      out.push(rec);
      console.log("@@PLAY " + JSON.stringify(rec));
    } catch (e) { }
  }

  var Gson = Java.use("com.google.gson.Gson");
  [["java.lang.String", "java.lang.Class"],
   ["java.lang.String", "java.lang.reflect.Type"]].forEach(function (sig) {
    try {
      var o = Gson.fromJson.overload.apply(Gson.fromJson, sig);
      o.implementation = function () {
        var args = Array.prototype.slice.call(arguments);
        var r = o.apply(this, args);
        try { if (typeof args[0] === "string") parse(args[0]); } catch (e) { }
        return r;
      };
    } catch (e) { }
  });
  console.log("@@ hooked Gson (play_count filter)");

  rpc.exports = {
    getlist: function () { return out; },
    count: function () { return out.length; },
    clear: function () { out = []; seen = {}; return 0; },
    rawcount: function () { return n; }
  };
});

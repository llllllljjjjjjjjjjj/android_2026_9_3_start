"use strict";
// 用户主页：hook Gson 解析，过滤含 follower_count / aweme_count 的响应
var seen = {};
var out = [];

Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return null; } }

  function num(json, k) {
    // 兼容 number / string / 负号 / 冒号前后任意空白
    var m = json.match(new RegExp('"' + k + '"\\s*:\\s*"?(-?\\d+)"?'));
    return m ? m[1] : null;
  }
  function str(json, k) {
    var m = json.match(new RegExp('"' + k + '"\\s*:\\s*"([^"]{0,200})"'));
    return m ? m[1] : null;
  }

  var diagDone = false;
  function diag(json) {
    if (diagDone) return;
    diagDone = true;
    var i = json.indexOf("follower_count");
    console.log("@@DIAG ctx=" + JSON.stringify(json.slice(Math.max(0, i - 60), i + 160)));
  }

  // 从 mix_follower_count 风格的嵌套串 {"<uid>":<count>} 提取
  function numMix(json, uid) {
    var m = json.match(new RegExp('\\\\+"' + uid + '\\\\+"\\s*:\\s*(\\d+)'));
    if (m) return m[1];
    m = json.match(new RegExp('"' + uid + '"\\s*:\\s*(\\d+)'));
    return m ? m[1] : null;
  }

  function parse(json) {
    try {
      if (!json || json.indexOf("follower_count") < 0) return;
      var uid = str(json, "uid") || str(json, "user_id") || str(json, "id");
      if (!uid) return;
      var rec = {
        uid: uid,
        secUid: str(json, "sec_uid"),
        nickname: str(json, "nickname"),
        uniqueId: str(json, "unique_id"),
        signature: str(json, "signature"),
        follower: num(json, "follower_count") || numMix(json, uid),
        following: num(json, "following_count"),
        awemeCount: num(json, "aweme_count"),
        totalFavorited: num(json, "total_favorited"),
        favoriting: num(json, "favoriting_count"),
        digg: num(json, "digg_count"),
        verify: str(json, "custom_verify") || str(json, "enterprise_verify_reason"),
        ipLocation: str(json, "ip_location"),
        gender: num(json, "gender"),
        birthday: str(json, "birthday")
      };
      var key = uid + "|" + (rec.follower || "");
      if (seen[key]) return;
      seen[key] = 1;
      if (!rec.follower) diag(json);
      out.push(rec);
      console.log("@@USER " + JSON.stringify(rec));
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
  console.log("@@ hooked Gson (user profile filter)");

  rpc.exports = {
    getlist: function () { return out; },
    count: function () { return out.length; },
    clear: function () { out = []; seen = {}; return 0; }
  };
});

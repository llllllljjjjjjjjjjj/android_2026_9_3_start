"use strict";
// 搜索结果视频卡：去重收集 + 多路取字段（getter / 字段 / 反射）
var seen = {};
var count = 0;

Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return null; } }

  function tryGet(obj, names) {
    for (var i = 0; i < names.length; i++) {
      var nm = names[i];
      try {
        if (obj && typeof obj[nm] === "function") {
          var v = obj[nm]();
          if (v !== null && v !== undefined) return S(v);
        }
      } catch (e) { }
    }
    return null;
  }

  function tryField(obj, names) {
    for (var i = 0; i < names.length; i++) {
      try {
        var f = obj[names[i]];
        if (f && typeof f.value !== "undefined") {
          var v = f.value;
          if (v !== null && v !== undefined) return S(v);
        }
      } catch (e) { }
    }
    return null;
  }

  function dump(a) {
    try {
      var aid = tryGet(a, ["getAid", "getAwemeId"]) || tryField(a, ["aid", "awemeId"]);
      if (!aid || seen[aid]) return;
      seen[aid] = 1;
      count++;
      var o = { aid: aid };
      o.desc = tryGet(a, ["getDesc", "getTitle"]) || tryField(a, ["desc", "title"]);
      o.createTime = tryGet(a, ["getCreateTime"]);
      o.awemeType = tryGet(a, ["getAwemeType"]);
      // author
      try {
        var au = a.getAuthor();
        if (au) o.author = tryGet(au, ["getNickname", "getUniqueId"]) || tryField(au, ["nickname", "uniqueId"]);
      } catch (e) { }
      // statistics
      try {
        var st = a.getStatistics();
        if (st) {
          o.digg = tryGet(st, ["getDiggCount"]);
          o.comment = tryGet(st, ["getCommentCount"]);
          o.share = tryGet(st, ["getShareCount"]);
          o.play = tryGet(st, ["getPlayCount"]);
        }
      } catch (e) { }
      try {
        var vd = a.getVideo();
        if (vd) {
          o.duration = tryGet(vd, ["getDuration"]);
          try { var pl = vd.getPlayAddr(); if (pl) o.playUrl = (tryGet(pl, ["getUri", "getUrlList"]) || "").slice(0, 60); } catch (e) { }
        }
      } catch (e) { }
      console.log("@@CARD " + JSON.stringify(o));
    } catch (e) { }
  }

  try {
    var SMF = Java.use("com.ss.android.ugc.aweme.discover.mixfeed.SearchMixFeed");
    SMF.getAweme.implementation = function () {
      var a = this.getAweme();
      try { if (a) dump(a); } catch (e) { }
      return a;
    };
    console.log("@@ hooked getAweme (dedup v2)");
  } catch (e) { console.log("@@ SMF err " + S(e)); }

  rpc.exports = {
    count: function () { return count; },
    list: function () { return Object.keys(seen); }
  };
});

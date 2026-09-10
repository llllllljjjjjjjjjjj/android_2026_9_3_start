"use strict";
// 通过 aid 拿视频/图文：精确提取 play_addr.url_list（视频）+ images（图文）
// 容错：无 play_addr 且无 images 时不丢弃，标记 unknown 供上层判断
var seen = {};
var out = [];
var diagDone = false;
var reqPaths = [];

Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return null; } }

  // ★ 风控健康：记录 detail / stats(播放上报) / app_log 路径
  try {
    var RB0 = Java.use("com.bytedance.retrofit2.RequestBuilder");
    var t0 = RB0.build.overload("com.bytedance.retrofit2.ExpandCallback");
    t0.implementation = function (cb) {
      var r = t0.call(this, cb);
      try {
        var u = S(r.getUrl()) || "";
        if (/aweme\/detail|aweme\/stats|app_log|multi\/aweme/.test(u)) {
          if (reqPaths.length < 300) reqPaths.push(u.length > 400 ? u.slice(0, 400) : u);
        }
      } catch (e) { }
      return r;
    };
  } catch (e) { }
  function unesc(s) { return s.replace(/\\\//g, "/"); }

  function num(json, k) {
    var m = json.match(new RegExp('"' + k + '"\\s*:\\s*"?(-?\\d+)"?'));
    return m ? m[1] : null;
  }
  function str(json, k) {
    var m = json.match(new RegExp('"' + k + '"\\s*:\\s*"([^"]{0,300})"'));
    return m ? m[1] : null;
  }

  // 精确取 anchor 之后的第一个 url_list 数组（括号配对，避免串到相邻字段）
  function urlsAfter(json, anchor) {
    var i = json.indexOf('"' + anchor + '"');
    if (i < 0) return null;
    var j = json.indexOf('"url_list"', i);
    if (j < 0) return null;
    var s = json.indexOf('[', j);
    if (s < 0) return null;
    var e = json.indexOf(']', s);
    if (e < 0) return null;
    var list = json.slice(s, e + 1).match(/"([^"]+)"/g);
    return list ? list.map(function (u) { return unesc(u.replace(/"/g, "")); }) : null;
  }

  // 括号配对精确定位 key 对应的数组
  function arrAfter(json, key) {
    var i = json.indexOf('"' + key + '"');
    if (i < 0) return null;
    var s = json.indexOf('[', i);
    if (s < 0) return null;
    var d = 0, e = -1, lim = Math.min(json.length, s + 200000);
    for (var p = s; p < lim; p++) {
      var c = json.charCodeAt(p);
      if (c === 91) d++;            // [
      else if (c === 93) { d--; if (d === 0) { e = p; break; } }   // ]
    }
    return e > s ? json.slice(s, e + 1) : null;
  }

  function urlListOf(objStr) {
    var j = objStr.indexOf('"url_list"');
    if (j < 0) return null;
    var s = objStr.indexOf('[', j);
    if (s < 0) return null;
    var e = objStr.indexOf(']', s);
    if (e < 0) return null;
    var list = objStr.slice(s, e + 1).match(/"([^"]+)"/g);
    return list ? list.map(function (u) { return unesc(u.replace(/"/g, "")); }) : null;
  }

  // 图片 CDN 特征
  function isImg(u) { return /douyinpic|tos-cn-i-|\.jpe?g|\.webp|\.heic|\.png/i.test(u); }

  // 图文：只在 images 数组内提取，兼容 download_url_list / url_list
  function imageUrls(json) {
    var arr = arrAfter(json, "images");
    if (!arr) return null;
    var re = /"(?:download_)?url_list"\s*:\s*\[([^\]]{0,1500})\]/g;
    var m, pics = [];
    while ((m = re.exec(arr)) !== null) {
      var one = m[1].match(/"([^"]+)"/g);
      if (!one) continue;
      // 每个图片元素里优选 webp（兼容性最好），其次 jpeg/png，最后 origin 原图
      var best = null, fallback = null;
      for (var k = 0; k < one.length; k++) {
        var u = unesc(one[k].replace(/"/g, ""));
        if (!isImg(u)) continue;
        if (/\.webp(\?|$)/i.test(u)) { best = u; break; }
        if (/\.(jpe?g|png)(\?|$)/i.test(u) && !best) best = u;
        if (!fallback) fallback = u;
      }
      if (best || fallback) pics.push(best || fallback);
      if (pics.length >= 40) break;
    }
    return pics.length ? pics : null;
  }

  function parse(json) {
    try {
      if (!json) return;
      var hasVideo = json.indexOf('"play_addr"') >= 0;
      var hasImages = json.indexOf('"images"') >= 0;
      if (!hasVideo && !hasImages) return;

      var aid = str(json, "aweme_id") || str(json, "aid");
      if (!aid) return;

      var play = hasVideo ? urlsAfter(json, "play_addr") : null;
      var pics = hasImages ? imageUrls(json) : null;
      var atype = num(json, "aweme_type");

      // 判定：有图片优先判为图文（图文也可能带 play_addr/背景音）
      var mediaType;
      if (pics && pics.length) mediaType = "album";
      else if (play && play.length) mediaType = "video";
      else mediaType = "unknown";

      // 首次遇到非视频类型时 dump 结构，便于校验判定
      if (!diagDone && (atype && atype !== "0")) {
        diagDone = true;
        var pi = json.indexOf('"images"');
        console.log("@@DIAG68 aweme_type=" + atype + " imgs=" + (pics ? pics.length : 0) +
          " play=" + (play ? play.length : 0));
        if (pi >= 0) console.log("@@DIAG68_IMG " + JSON.stringify(json.slice(pi, pi + 300)));
      }

      var rec = {
        aid: aid,
        mediaType: mediaType,
        awemeType: atype,
        desc: str(json, "desc"),
        duration: num(json, "duration"),
        width: num(json, "width"),
        height: num(json, "height"),
        playUrl: play || [],
        imageCount: pics ? pics.length : 0,
        imageUrl: pics || [],
        cover: urlsAfter(json, "cover") || [],
        downloadAddr: urlsAfter(json, "download_addr") || [],
        digg: num(json, "digg_count"),
        comment: num(json, "comment_count"),
        share: num(json, "share_count"),
        collect: num(json, "collect_count"),
        bitRate: num(json, "bit_rate"),
        codecType: str(json, "codec_type")
      };

      var key = aid + "|" + mediaType + "|" + (rec.playUrl[0] || rec.imageUrl[0] || "");
      if (seen[key]) return;
      seen[key] = 1;
      out.push(rec);
      console.log("@@MEDIA " + JSON.stringify({
        aid: aid, type: mediaType, awemeType: rec.awemeType,
        imgs: rec.imageCount, url: (rec.playUrl[0] || rec.imageUrl[0] || "<none>").slice(0, 100)
      }));
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
  console.log("@@ hooked Gson (video + album)");

  rpc.exports = {
    // ★ 风控健康：请求路径记录
    getpaths: function () { return reqPaths; },
    cleardpaths: function () { reqPaths = []; return 0; },
    openurl: function (url) {
      var ok = 0;
      try {
        var AT = Java.use("android.app.ActivityThread");
        var ctx = AT.currentApplication().getApplicationContext();
        var Intent = Java.use("android.content.Intent");
        var Uri = Java.use("android.net.Uri");
        var i = Intent.$new("android.intent.action.VIEW", Uri.parse(url));
        i.addFlags(0x10000000);
        ctx.startActivity(i);
        ok = 1;
      } catch (e) { }
      return ok;
    },
    getlist: function () { return out; },
    count: function () { return out.length; },
    clear: function () { out = []; seen = {}; reqPaths = []; return 0; }
  };
});

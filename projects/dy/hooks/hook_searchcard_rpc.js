"use strict";
// 搜索结果卡片：RPC 返回（避免 stdout 编码破坏中文）
var seen = {};
var cards = [];
var reqPaths = [];

Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return null; } }

  // ★ 风控健康：记录所有请求路径（业务 + 埋点），用于配对校验
  try {
    var RB0 = Java.use("com.bytedance.retrofit2.RequestBuilder");
    var t0 = RB0.build.overload("com.bytedance.retrofit2.ExpandCallback");
    t0.implementation = function (cb) {
      var r = t0.call(this, cb);
      try {
        var p = S(r.getPath());
        if (p && (p.indexOf("search") >= 0 || p.indexOf("comment") >= 0
                  || p.indexOf("app_log") >= 0 || p.indexOf("upload_ei") >= 0
                  || p.indexOf("aweme/stats") >= 0 || p.indexOf("detail") >= 0)) {
          if (reqPaths.length < 300) {
            // 只记路径+关键 query，不记全 URL（避免体积）
            var u = S(r.getUrl()) || "";
            reqPaths.push(u.length > 400 ? u.slice(0, 400) : u);
          }
        }
      } catch (e) { }
      return r;
    };
    console.log("@@ path recorder on");
  } catch (e) { console.log("@@ path recorder err " + S(e)); }

  // 反射拿顶部 Activity（frida 直读 Map 受限，全程走反射）
  function topActivity() {
    try {
      var AT = Java.use("android.app.ActivityThread");
      var thread = AT.currentActivityThread();
      if (!thread) return null;
      var f = thread.getClass().getDeclaredField("mActivities");
      f.setAccessible(true);
      var map = f.get(thread);
      if (!map) return null;
      var vs = map.getClass().getMethod("values").invoke(map, []);
      var it = vs.getClass().getMethod("iterator").invoke(vs, []);
      var icls = it.getClass();
      var hasNext = icls.getMethod("hasNext").invoke(it, []);
      var first = null, guard = 0;
      while (hasNext && guard < 50) {
        guard++;
        var rec = icls.getMethod("next").invoke(it, []);
        try {
          var af = rec.getClass().getDeclaredField("activity");
          af.setAccessible(true);
          var a = af.get(rec);
          if (a) {
            if (!first) first = a;
            if (S(a.getClass().getName()).indexOf("aweme") >= 0) return a;
          }
        } catch (e) { }
        hasNext = icls.getMethod("hasNext").invoke(it, []);
      }
      return first;
    } catch (e) { console.log("@@ topActivity err " + S(e)); return null; }
  }

  function tryGet(obj, names) {
    for (var i = 0; i < names.length; i++) {
      try {
        if (obj && typeof obj[names[i]] === "function") {
          var v = obj[names[i]]();
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

  // 返回 Java 对象（用于 author 这类嵌套字段）
  function fieldObj(obj, names) {
    for (var i = 0; i < names.length; i++) {
      try {
        var f = obj[names[i]];
        if (f && f.value) return f.value;
      } catch (e) { }
    }
    return null;
  }

  function collect(a) {
    try {
      var aid = tryGet(a, ["getAid", "getAwemeId"]) || tryField(a, ["aid", "awemeId"]);
      if (!aid || seen[aid]) return;
      seen[aid] = 1;
      var o = { aid: aid };
      o.desc = tryGet(a, ["getDesc", "getTitle"]) || tryField(a, ["desc", "title"]);
      o.createTime = tryGet(a, ["getCreateTime"]);
      o.awemeType = tryGet(a, ["getAwemeType"]);
      try {
        // Aweme.author 是 public 字段（无 getAuthor()）
        var au = fieldObj(a, ["author"]);
        if (au) {
          o.authorCls = S(au.getClass().getName());
          o.author = tryField(au, ["nickname", "nickName", "name"]) || tryGet(au, ["getNickname"]);
          o.uid = tryField(au, ["uid", "userId"]) || tryGet(au, ["getUid"]);
          o.secUid = tryField(au, ["secUid"]) || tryGet(au, ["getSecUid"]);
          o.uniqueId = tryField(au, ["uniqueId", "shortId"]);
        } else {
          o.authorNull = "yes";
        }
      } catch (e) { o.authorErr = String(e).slice(0, 60); }
      try {
        var st = a.getStatistics();
        if (st) {
          o.digg = tryField(st, ["diggCount"]) || tryGet(st, ["getDiggCount"]);
          o.comment = tryField(st, ["commentCount"]) || tryGet(st, ["getCommentCount"]);
          o.share = tryField(st, ["shareCount"]) || tryGet(st, ["getShareCount"]);
          o.collect = tryField(st, ["collectCount"]) || tryGet(st, ["getCollectCount"]);
          o.play = tryField(st, ["playCount"]) || tryGet(st, ["getPlayCount"]);
          o.forward = tryField(st, ["forwardCount"]);
          o.download = tryField(st, ["downloadCount"]);
          o.exposure = tryField(st, ["exposureCount"]);
          o.recommend = tryField(st, ["recommendCount"]);
        }
      } catch (e) { }
      try {
        var vd = a.getVideo();
        if (vd) {
          o.duration = tryField(vd, ["videoLength", "longVideoRealDuration", "duration"]) || tryGet(vd, ["getDuration", "getVideoLength"]);
        }
      } catch (e) { }
      try { o.createTime = tryField(a, ["createTime"]) || tryGet(a, ["getCreateTime"]); } catch (e) { }
      try { o.textExtra = tryField(a, ["textExtra"]) ? "yes" : null; } catch (e) { }
      cards.push(o);
    } catch (e) { }
  }

  var SMF = Java.use("com.ss.android.ugc.aweme.discover.mixfeed.SearchMixFeed");
  SMF.getAweme.implementation = function () {
    var a = this.getAweme();
    try { if (a) collect(a); } catch (e) { }
    return a;
  };
  console.log("[*] hooked (rpc-collect)");

  rpc.exports = {
    // ★ 风控健康：记录所有业务/埋点请求路径（供 Python 侧做配对校验）
    getpaths: function () { return reqPaths; },
    cleardpaths: function () { reqPaths = []; return 0; },
    // RPC 触发：用 App 自身的 Activity 上下文打开 deeplink（不再依赖 adb am start）
    openurl: function (url) {
      var ok = 0;
      try {
        var AT = Java.use("android.app.ActivityThread");
        var app = AT.currentApplication();
        if (!app) { console.log("@@ openurl: no application"); return -1; }
        var ctx = app.getApplicationContext();
        var Intent = Java.use("android.content.Intent");
        var Uri = Java.use("android.net.Uri");
        var i = Intent.$new("android.intent.action.VIEW", Uri.parse(url));
        i.addFlags(0x10000000); // FLAG_ACTIVITY_NEW_TASK
        ctx.startActivity(i);
        ok = 1;
      } catch (e) { console.log("@@ openurl err " + S(e)); }
      return ok;
    },
    // RPC 回到桌面（替代 adb keyevent HOME）
    gohome: function () {
      var ok = 0;
      try {
        var AT = Java.use("android.app.ActivityThread");
        var ctx = AT.currentApplication().getApplicationContext();
        var Intent = Java.use("android.content.Intent");
        var i = Intent.$new("android.intent.action.MAIN");
        i.addCategory("android.intent.category.HOME");
        i.addFlags(0x10000000);
        ctx.startActivity(i);
        ok = 1;
      } catch (e) { console.log("@@ gohome err " + S(e)); }
      return ok;
    },
    // RPC 滚动（替代 adb input swipe）：向顶部 Activity 的 DecorView 派发触摸事件
    scroll: function (dy) {
      var info = { found: 0, cls: null, h: 0 };
      try {
        var act = topActivity();
        if (!act) {
          // 兜底：指定类枚举
          Java.choose("com.ss.android.ugc.aweme.search.activity.SearchResultActivity", {
            onMatch: function (a) { if (!act) act = a; },
            onComplete: function () { }
          });
        }
        if (!act) { console.log("@@ scroll: no activity"); return 0; }
        info.found = 1;
        info.cls = S(act.getClass().getName());
        var w = act.getWindow();
        var dv = w ? w.getDecorView() : null;
        if (!dv) { console.log("@@ scroll: no decorview"); return 0; }
        var h = dv.getHeight(), wd = dv.getWidth();
        info.h = h;
        if (h <= 0 || wd <= 0) return 0;
        var d = (typeof dy === "number" && dy !== 0) ? dy : Math.round(h * 0.7);
        Java.scheduleOnMainThread(function () {
          try {
            var ME = Java.use("android.view.MotionEvent");
            var SC = Java.use("android.os.SystemClock");
            var t0 = SC.uptimeMillis();
            var cx = wd / 2;
            var y1 = h * 0.75, y2 = y1 - d;
            var e1 = ME.obtain(t0, t0, 0, cx, y1, 0);
            var e2 = ME.obtain(t0, t0 + 60, 2, cx, (y1 + y2) / 2, 0);
            var e3 = ME.obtain(t0, t0 + 120, 2, cx, y2, 0);
            var e4 = ME.obtain(t0, t0 + 180, 1, cx, y2, 0);
            dv.dispatchTouchEvent(e1);
            dv.dispatchTouchEvent(e2);
            dv.dispatchTouchEvent(e3);
            dv.dispatchTouchEvent(e4);
          } catch (e) { console.log("@@ swipe err " + S(e)); }
        });
      } catch (e) { console.log("@@ scroll err " + S(e)); }
      console.log("@@ scrollinfo " + JSON.stringify(info));
      return info.found;
    },
    getcards: function () { return cards; },
    count: function () { return cards.length; },
    clear: function () { cards = []; seen = {}; return 0; }
  };
  console.log("[*] rpc ready");
});

"use strict";
// 按 aid 拿评论（RPC / 数据层）：
//   CommentItemList 的 comments 字段才是数据本体（items 全是 null）
//   路径：ChunkDataStream 代理 → Gson.toJson(chunk) → 解析 comments 数组
//   明文可得：cid / aweme_id / digg_count / create_time / reply_comment_total / 用户信息
//   文本：在 comment_token（加密），需另行解密
var seen = {};
var out = [];
var chunkN = 0;
var diagDone = false;
var reqPaths = [];

Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return null; } }

  // ★ 风控健康：记录业务/埋点请求路径
  try {
    var RB0 = Java.use("com.bytedance.retrofit2.RequestBuilder");
    var t0 = RB0.build.overload("com.bytedance.retrofit2.ExpandCallback");
    t0.implementation = function (cb) {
      var r = t0.call(this, cb);
      try {
        var u = S(r.getUrl()) || "";
        if (/comment|app_log|aweme\/detail|aweme\/stats|upload_ei|search/.test(u)) {
          if (reqPaths.length < 300) reqPaths.push(u.length > 400 ? u.slice(0, 400) : u);
        }
      } catch (e) { }
      return r;
    };
    console.log("@@ path recorder on");
  } catch (e) { }
  function unesc(s) { return s.replace(/\\n/g, " ").replace(/\\"/g, '"').replace(/\\\//g, "/"); }

  function pick(seg, k) {
    var m = seg.match(new RegExp('"' + k + '"\\s*:\\s*"((?:[^"\\\\]|\\\\.){0,600})"'));
    return m ? unesc(m[1]) : null;
  }
  function num(seg, k) {
    var m = seg.match(new RegExp('"' + k + '"\\s*:\\s*(-?\\d+)'));
    return m ? m[1] : null;
  }

  function parseComments(json) {
    var i = json.indexOf('"comments"');
    if (i < 0) return 0;
    var s = json.indexOf('[', i);
    if (s < 0) return 0;
    var d = 0, e = -1;
    for (var p = s; p < json.length; p++) {
      var c = json.charCodeAt(p);
      if (c === 91) d++;
      else if (c === 93) { d--; if (d === 0) { e = p; break; } }
    }
    if (e < 0) return 0;
    var arr = json.slice(s, e + 1);

    var re = /"cid"\s*:\s*"(\d+)"/g, m, marks = [];
    while ((m = re.exec(arr)) !== null) marks.push({ cid: m[1], at: m.index });

    var added = 0;
    for (var k = 0; k < marks.length; k++) {
      var end = (k + 1 < marks.length) ? marks[k + 1].at : Math.min(arr.length, marks[k].at + 30000);
      var seg = arr.slice(marks[k].at, end);
      var cid = marks[k].cid;
      if (seen[cid]) continue;
      seen[cid] = 1;
      var rec = {
        cid: cid,
        text: pick(seg, "text"),
        digg: num(seg, "digg_count"),
        createTime: num(seg, "create_time"),
        replyTotal: num(seg, "reply_comment_total"),
        stickPosition: num(seg, "stick_position"),
        status: num(seg, "status"),
        content_type: num(seg, "content_type"),
        isAuthorDigged: pick(seg, "is_author_digged"),
        commentTokenLen: (function () { var t = pick(seg, "comment_token"); return t ? t.length : 0; })(),
        ipLabel: pick(seg, "ip_label"),
        nickname: pick(seg, "nickname"),
        uid: pick(seg, "uid"),
        secUid: pick(seg, "sec_uid"),
        uniqueId: pick(seg, "unique_id"),
        imageCount: (function () {
          var m2 = seg.match(/"image_list"\s*:\s*\[/);
          if (!m2) return 0;
          var cnt = seg.slice(m2.index).match(/"url_list"/g);
          return cnt ? cnt.length : 0;
        })()
      };
      out.push(rec);
      added++;
    }
    return added;
  }

  try {
    var CDS = Java.use("com.bytedance.android.chunkstreamprediction.network.ChunkDataStream");
    var Obs = Java.use("com.bytedance.android.chunkstreamprediction.network.ChunkDataObserver");
    var idx = 0;
    CDS.subscribe.implementation = function (observer) {
      idx++;
      var tag = idx;
      try {
        var Proxy = Java.registerClass({
          name: "com.dy.cmt2.P" + tag,
          implements: [Obs],
          methods: {
            onNext: function (t) {
              try {
                if (t) {
                  var cn = S(t.getClass().getName());
                  chunkN++;
                  if (cn.indexOf("CommentItemList") >= 0) {
                    var Gson = Java.use("com.google.gson.Gson");
                    var js = String(Gson.$new().toJson(t));
                    if (!diagDone) {
                      diagDone = true;
                      console.log("@@DIAG jsonLen=" + js.length +
                        " hasComments=" + (js.indexOf('"comments"') >= 0) +
                        " hasItems=" + (js.indexOf('"items"') >= 0) +
                        " hasText=" + (js.indexOf('"text"') >= 0));
                    }
                    var added = parseComments(js);
                    console.log("@@CMT +" + added + " total=" + out.length +
                      " chunk=" + chunkN + " jsonLen=" + js.length);
                  }
                }
              } catch (e) { console.log("@@e " + S(e)); }
              try { return observer.onNext(t); } catch (e2) { return null; }
            },
            onComplete: function () { try { return observer.onComplete(); } catch (e) { return null; } },
            onFailed: function (th) { try { return observer.onFailed(th); } catch (e) { return null; } }
          }
        });
        return this.subscribe(Proxy.$new());
      } catch (e) { return this.subscribe(observer); }
    };
    console.log("@@ hooked ChunkDataStream (comments field)");
  } catch (e) { console.log("@@ err " + S(e)); }

  rpc.exports = {
    // ★ 风控健康：请求路径记录
    getpaths: function () { return reqPaths; },
    cleardpaths: function () { reqPaths = []; return 0; },
    // 通用 RPC 触达：App 自身 Activity 上下文打开 deeplink（无 adb）
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
      } catch (e) { console.log("@@ openurl err " + S(e)); }
      return ok;
    },
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
      } catch (e) { }
      return ok;
    },
    // RPC 打开评论区：遍历 View 树定位评论入口并 performClick（业务回调，非屏幕事件）
    opencomments: function () {
      var info = { tried: 0, hit: null };
      try {
        var act = null;
        Java.choose("com.ss.android.ugc.aweme.detail.ui.DetailActivity", {
          onMatch: function (a) { if (!act) act = a; }, onComplete: function () { }
        });
        if (!act) {
          Java.choose("android.app.Activity", {
            onMatch: function (a) {
              try {
                if (!act && S(a.getClass().getName()).indexOf("aweme") >= 0) act = a;
              } catch (e) { }
            }, onComplete: function () { }
          });
        }
        if (!act) { console.log("@@ opencomments: no activity"); return -1; }
        var w = act.getWindow();
        var root = w ? w.getDecorView() : null;
        if (!root) return -2;

        var hits = [];
        function walk(v, depth) {
          if (!v || depth > 30) return;
          try {
            info.tried++;
            try {
              var id = v.getId();
              if (id !== -1 && id !== undefined) {
                var nm = "";
                try { nm = String(v.getResources().getResourceEntryName(id)); } catch (e) { }
                if (nm === "comment_container" || nm === "comment_layout") {
                  hits.push({ v: v, kind: nm });
                }
              }
            } catch (e) { }
          } catch (e) { }
          try {
            var vg = Java.cast(v, Java.use("android.view.ViewGroup"));
            if (vg) {
              var cc = vg.getChildCount();
              for (var i = 0; i < cc; i++) walk(vg.getChildAt(i), depth + 1);
            }
          } catch (e) { }
        }

        walk(root, 0);
        info.hits = hits.length;
        if (!hits.length) { console.log("@@ opencomments: no container (tried=" + info.tried + ")"); return -3; }

        // 逐个尝试点击容器及其可点击祖先（业务回调，非屏幕事件）
        for (var hi = 0; hi < hits.length && hi < 6; hi++) {
          var node = hits[hi].v;
          info.hit = S(node.getClass().getName());
          var cc2 = node;
          for (var up = 0; up < 4 && cc2; up++) {
            try {
              if (cc2.isClickable()) break;
            } catch (e) { }
            try { cc2 = Java.cast(cc2.getParent(), Java.use("android.view.View")); } catch (e) { cc2 = null; }
          }
          var finalNode = cc2 || node;
          Java.scheduleOnMainThread(function () {
            try { finalNode.performClick(); } catch (e) { console.log("@@ click err " + S(e)); }
          });
          info.clicked = S(finalNode.getClass().getName());
          (function () { var t0 = Date.now(); while (Date.now() - t0 < 2500) { } })();
        }
      } catch (e) { console.log("@@ opencomments err " + S(e)); }
      console.log("@@ opencomments " + JSON.stringify(info));
      return info.hit ? 1 : 0;
    },
    // RPC 滚动（评论区翻页）：向 App 顶部 Activity 的 DecorView 派发触摸事件
    scroll: function (dy) {
      var info = { found: 0, cls: null, h: 0 };
      try {
        var act = null;
        Java.choose("com.ss.android.ugc.aweme.detail.ui.DetailActivity", {
          onMatch: function (a) { if (!act) act = a; }, onComplete: function () { }
        });
        if (!act) {
          Java.choose("android.app.Activity", {
            onMatch: function (a) {
              try {
                if (!act && S(a.getClass().getName()).indexOf("aweme") >= 0) act = a;
              } catch (e) { }
            }, onComplete: function () { }
          });
        }
        if (!act) { console.log("@@ cmt scroll: no activity"); return 0; }
        info.found = 1;
        info.cls = S(act.getClass().getName());
        var w = act.getWindow();
        var dv = w ? w.getDecorView() : null;
        if (!dv) return 0;
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
          } catch (e) { console.log("@@ cmt swipe err " + S(e)); }
        });
      } catch (e) { console.log("@@ cmt scroll err " + S(e)); }
      return info.found;
    },
    getlist: function () { return out; },
    count: function () { return out.length; },
    clear: function () { out = []; seen = {}; chunkN = 0; diagDone = false; return 0; }
  };
});

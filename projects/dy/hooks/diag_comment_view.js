"use strict";
// 诊断：列出所有 comment 相关 View 的完整信息（含可点击性、祖先链）
Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }

  function dumpTree(root) {
    var found = [];
    var seen = 0;

    function info(v) {
      var o = {};
      try { o.cls = S(v.getClass().getName()); } catch (e) { }
      try { o.id = S(v.getId()); } catch (e) { }
      try { o.idName = String(v.getResources().getResourceEntryName(v.getId())); } catch (e) { }
      try { o.clickable = v.isClickable(); } catch (e) { }
      try { o.desc = S(v.getContentDescription()); } catch (e) { }
      try { var b = Java.use("android.graphics.Rect"); var r = b.$new(); v.getGlobalVisibleRect(r);
            o.bounds = "[" + r.left + "," + r.top + "][" + r.right + "," + r.bottom + "]"; } catch (e) { }
      try { o.vis = v.getVisibility(); } catch (e) { }
      return o;
    }

    function walk(v, depth, path) {
      if (!v || depth > 30 || seen > 2000) return;
      seen++;
      try {
        var nm = "";
        try { nm = String(v.getResources().getResourceEntryName(v.getId())); } catch (e) { }
        var cd = "";
        try { cd = S(v.getContentDescription()); } catch (e) { }
        if (nm.indexOf("comment") >= 0 || (cd && cd.indexOf("评论") >= 0)) {
          found.push({ path: path, info: info(v) });
        }
      } catch (e) { }
      try {
        var vg = Java.cast(v, Java.use("android.view.ViewGroup"));
        if (vg) {
          var cc = vg.getChildCount();
          for (var i = 0; i < cc; i++) walk(vg.getChildAt(i), depth + 1, path + "/" + i);
        }
      } catch (e) { }
    }
    walk(root, 0, "");
    return { found: found, scanned: seen };
  }

  // 反射取顶部 Activity（frida 对抽象类 Java.choose 不可靠）
  function topActivity() {
    try {
      var AT = Java.use("android.app.ActivityThread");
      var th = AT.currentActivityThread();
      if (!th) return null;
      var f = th.getClass().getDeclaredField("mActivities");
      f.setAccessible(true);
      var map = f.get(th);
      if (!map) return null;
      var vs = map.getClass().getMethod("values", []).invoke(map, []);
      var it = vs.getClass().getMethod("iterator", []).invoke(vs, []);
      var ic = it.getClass();
      var hn = ic.getMethod("hasNext", []).invoke(it, []);
      var best = null, g = 0;
      while (hn && g < 50) {
        g++;
        var rec = ic.getMethod("next").invoke(it, []);
        try {
          var af = rec.getClass().getDeclaredField("activity");
          af.setAccessible(true);
          var a = af.get(rec);
          if (a) {
            if (!best) best = a;
            if (S(a.getClass().getName()).indexOf("aweme") >= 0) return a;
          }
        } catch (e) { }
        hn = ic.getMethod("hasNext").invoke(it, []);
      }
      return best;
    } catch (e) { console.log("@@ topActivity err " + S(e)); return null; }
  }

  rpc.exports = {
    dump: function () {
      var res = { ok: 0 };
      try {
        var act = topActivity();
        if (!act) { res.err = "no activity"; return res; }
        res.act = S(act.getClass().getName());
        var w = act.getWindow();
        res.win = w ? "ok" : "null";
        var dv = w ? w.getDecorView() : null;
        if (!dv) { res.err = "no decorview"; return res; }
        var t = dumpTree(dv);
        res.scanned = t.scanned;
        res.count = t.found.length;
        res.items = t.found;
        res.ok = 1;
      } catch (e) { res.err = S(e); }
      return res;
    }
  };
  console.log("@@ rpc ready (view dump)");
});

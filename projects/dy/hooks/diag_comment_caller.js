"use strict";
// 定位评论请求的发起者：hook RequestBuilder.build，过滤 comment/list，打印调用栈
var n = 0;
Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }
  function stack() {
    try {
      var Log = Java.use("android.util.Log");
      var Th = Java.use("java.lang.Throwable");
      var full = String(Log.getStackTraceString(Th.$new()));
      var lines = full.split("\n");
      var keep = [];
      for (var i = 0; i < lines.length && keep.length < 22; i++) {
        var l = lines[i].trim();
        if (!l) continue;
        // 只保留 com.ss / com.bytedance 的业务帧
        if (/^\s*at (com\.ss\.|com\.bytedance\.|X\.)/.test(lines[i]) || i < 3) keep.push(l);
      }
      return keep.join(" | ");
    } catch (e) { return "<no stack>"; }
  }

  try {
    var RB = Java.use("com.bytedance.retrofit2.RequestBuilder");
    var t = RB.build.overload("com.bytedance.retrofit2.ExpandCallback");
    t.implementation = function (cb) {
      var r = t.call(this, cb);
      try {
        var p = S(r.getPath());
        if (/comment\/list/i.test(p)) {
          n++;
          if (n <= 2) {
            console.log("@@CREQ[" + n + "] " + S(r.getMethod()) + " " + S(r.getUrl()));
            console.log("@@CSTACK[" + n + "] " + stack());
          }
        }
      } catch (e) { }
      return r;
    };
    console.log("@@ hooked RequestBuilder.build (comment caller diag)");
  } catch (e) { console.log("@@ err " + S(e)); }
});

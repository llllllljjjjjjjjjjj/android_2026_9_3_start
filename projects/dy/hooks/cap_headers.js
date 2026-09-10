"use strict";
// 安全捕获 native 追加的完整 header
// 策略：只 hook【低频】的 client.Request.Builder.build()，且【不在回调内做任何对象构造】
//       仅做字符串拼接（历史崩溃原因是热路径 + 构造 JSONObject）
var dumped = 0;
var MAX = 3;

Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }

  function dumpHeaders(req, tag) {
    var out = [];
    try {
      var hs = req.getHeaders();
      if (!hs) return;
      var n = 0;
      try { n = hs.size(); } catch (e) { return; }
      if (n <= 0) return;
      for (var i = 0; i < n; i++) {
        try {
          var h = hs.get(i);
          out.push(String(h.getName()) + ":" + String(h.getValue()));
        } catch (e) { }
      }
    } catch (e) { return; }
    if (!out.length) return;
    dumped++;
    console.log("@@HDR" + dumped + " count=" + out.length + " tag=" + tag);
    // 用分隔符拼接，Python 侧再拆（避免 JSON 构造引发的 JNI 问题）
    console.log("@@HDRDATA " + out.join("\n"));
  }

  try {
    var B = Java.use("com.bytedance.retrofit2.client.Request$Builder");
    if (B.build) {
      B.build.overloads.forEach(function (o) {
        o.implementation = function () {
          var r = o.call(this, Array.prototype.slice.call(arguments));
          try {
            if (dumped < MAX) {
              var p = "";
              try { p = S(r.getPath()); } catch (e) { }
              if (/search|comment/i.test(p)) dumpHeaders(r, p);
            }
          } catch (e) { }
          return r;
        };
      });
      console.log("@@ hooked client.Request$Builder.build (safe)");
    }
  } catch (e) { console.log("@@ err " + S(e)); }

  rpc.exports = { reset: function () { dumped = 0; return 1; }, count: function () { return dumped; } };
});

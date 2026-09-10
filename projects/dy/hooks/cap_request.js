"use strict";
// 协议直发验证（单脚本）：捕获真实评论请求的 URL + header + body
// 供 Python 侧复用做直发测试
var cap = null;
var n = 0;

Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }

  try {
    var RB = Java.use("com.bytedance.retrofit2.RequestBuilder");
    var t = RB.build.overload("com.bytedance.retrofit2.ExpandCallback");
    t.implementation = function (cb) {
      var r = t.call(this, cb);
      try {
        var p = S(r.getPath());
        if (/comment\/list/i.test(p) && n < 3) {
          n++;
          var url = S(r.getUrl());
          var hdrs = {}, cnt = -1;
          try {
            var hs = r.getHeaders();
            if (hs) {
              cnt = hs.size();
              for (var i = 0; i < cnt; i++) {
                var h = hs.get(i);
                try { hdrs[String(h.getName())] = String(h.getValue()); } catch (e) { }
              }
            }
          } catch (e) { hdrs._err = S(e); }
          var body = null;
          try {
            var b = r.getBody();
            if (b) {
              var baos = Java.use("java.io.ByteArrayOutputStream").$new();
              b.writeTo(baos);
              body = String(baos.toString("UTF-8"));
            }
          } catch (e) { }
          if (n === 1) {
            cap = {
              method: S(r.getMethod()), url: url,
              headerCount: cnt, headers: hdrs,
              body: body, bodyLen: body ? body.length : 0,
              path: p
            };
          }
          console.log("@@CAP" + n + " method=" + S(r.getMethod()) +
            " urlLen=" + (url || "").length + " headers=" + cnt +
            " bodyLen=" + (body ? body.length : 0));
        }
      } catch (e) { console.log("@@ err " + S(e)); }
      return r;
    };
    console.log("@@ hooked (single-script capture)");
  } catch (e) { console.log("@@ hook err " + S(e)); }

  rpc.exports = {
    get: function () { return cap; },
    count: function () { return n; },
    reset: function () { cap = null; n = 0; return 1; }
  };
});

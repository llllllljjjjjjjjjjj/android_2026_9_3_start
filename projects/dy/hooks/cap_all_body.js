"use strict";
// 抓所有 POST 请求的 body（Java 层 RequestBuilder）——供 x-ss-stub 算法验证
var caps = [];

Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }
  try {
    var RB = Java.use("com.bytedance.retrofit2.RequestBuilder");
    var t = RB.build.overload("com.bytedance.retrofit2.ExpandCallback");
    t.implementation = function (cb) {
      var r = t.call(this, cb);
      try {
        var p = S(r.getPath());
        var m = S(r.getMethod());
        if (m === "POST" && caps.length < 8) {
          var url = S(r.getUrl());
          var body = null;
          try {
            var b = r.getBody();
            if (b) {
              var baos = Java.use("java.io.ByteArrayOutputStream").$new();
              b.writeTo(baos);
              body = String(baos.toString("UTF-8"));
            }
          } catch (e) { }
          caps.push({ method: m, path: p, url: url, body: body, bodyLen: body ? body.length : 0 });
          console.log("@@BODY method=" + m + " path=" + p.slice(0, 60) +
            " bodyLen=" + (body ? body.length : 0));
        }
      } catch (e) { console.log("@@ err " + S(e)); }
      return r;
    };
    console.log("@@ hooked all-post-body");
  } catch (e) { console.log("@@ hook err " + S(e)); }

  rpc.exports = {
    get: function () { return caps; },
    reset: function () { caps = []; return 1; }
  };
});

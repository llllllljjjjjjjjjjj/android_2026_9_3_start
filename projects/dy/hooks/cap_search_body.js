"use strict";
// 抓搜索请求的 body（Java 层 RequestBuilder）——与 cap_h2_headers.js(SSL_write HEADERS) 配对
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
        if (/search\/general\/stream/i.test(p) && n < 2) {
          n++;
          var url = S(r.getUrl());
          var hdrs = {};
          try {
            var hs = r.getHeaders();
            if (hs) {
              for (var i = 0; i < hs.size(); i++) {
                var h = hs.get(i);
                try { hdrs[String(h.getName())] = String(h.getValue()); } catch (e) { }
              }
            }
          } catch (e) { }
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
            cap = { method: S(r.getMethod()), url: url, headers: hdrs, body: body, path: p };
          }
          console.log("@@SEARCHBODY method=" + S(r.getMethod()) +
            " urlLen=" + (url || "").length + " hdrs=" + Object.keys(hdrs).length +
            " bodyLen=" + (body ? body.length : 0));
        }
      } catch (e) { console.log("@@ err " + S(e)); }
      return r;
    };
    console.log("@@ hooked search-request-body");
  } catch (e) { console.log("@@ hook err " + S(e)); }

  rpc.exports = {
    get: function () { return cap; },
    count: function () { return n; },
    reset: function () { cap = null; n = 0; return 1; }
  };
});

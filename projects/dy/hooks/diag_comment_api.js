"use strict";
// 评论接口诊断：同时看 请求层(URL) + org.json 路径 + Gson 路径
var reqN = 0, jsonN = 0;

Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }

  // 1) 请求层：过滤 comment 相关请求
  try {
    var RB = Java.use("com.bytedance.retrofit2.RequestBuilder");
    var t = RB.build.overload("com.bytedance.retrofit2.ExpandCallback");
    t.implementation = function (cb) {
      var r = t.call(this, cb);
      try {
        var p = S(r.getPath());
        if (/comment/i.test(p)) {
          reqN++;
          console.log("@@CREQ[" + reqN + "] " + S(r.getMethod()) + " " + S(r.getUrl()));
          try {
            var b = r.getBody();
            if (b) {
              var baos = Java.use("java.io.ByteArrayOutputStream").$new();
              b.writeTo(baos);
              console.log("@@CREQ_BODY " + String(baos.toString("UTF-8")).slice(0, 600));
            }
          } catch (e2) { }
        }
      } catch (e) { }
      return r;
    };
    console.log("@@ hooked RequestBuilder.build");
  } catch (e) { console.log("@@ RB err " + S(e)); }

  // 2) org.json 路径
  try {
    var JT = Java.use("com.bytedance.aweme.coffee.json.JSONTokenerGetter");
    JT.get.implementation = function (s) {
      try {
        var t2 = S(s);
        if (t2 && t2.indexOf('"cid"') >= 0 && jsonN < 3) {
          jsonN++;
          console.log("@@CJSON[" + jsonN + "] len=" + t2.length + " head=" + JSON.stringify(t2.slice(0, 400)));
        }
      } catch (e) { }
      return this.get(s);
    };
    console.log("@@ hooked JSONTokenerGetter");
  } catch (e) { }

  // 3) Gson 路径
  try {
    var Gson = Java.use("com.google.gson.Gson");
    var seenN = 0;
    [["java.lang.String", "java.lang.Class"],
     ["java.lang.String", "java.lang.reflect.Type"]].forEach(function (sig) {
      try {
        var o = Gson.fromJson.overload.apply(Gson.fromJson, sig);
        o.implementation = function () {
          var args = Array.prototype.slice.call(arguments);
          var r = o.apply(this, args);
          try {
            var s = args[0];
            if (typeof s === "string" && s.indexOf('"cid"') >= 0 && seenN < 3) {
              seenN++;
              console.log("@@CGSON[" + seenN + "] len=" + s.length + " head=" + JSON.stringify(s.slice(0, 400)));
            }
          } catch (e) { }
          return r;
        };
      } catch (e) { }
    });
    console.log("@@ hooked Gson");
  } catch (e) { }

  rpc.exports = { counts: function () { return { req: reqN, json: jsonN }; } };
});

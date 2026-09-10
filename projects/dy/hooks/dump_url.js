"use strict";
// 安全低侵入：捕获真实完整 URL（含 TTNet 追加的公共参数 query）
// 只在 URL/URI 构造时做字符串判断，不构造对象、不碰热路径
var FILTER = /search|suggest/i;
var n = 0;

Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }

  function report(u, via) {
    var s = S(u);
    if (!FILTER.test(s)) return;
    n++;
    console.log("@@URL[" + n + "] via=" + via);
    console.log("@@URLTXT " + s);
  }

  try {
    var URL = Java.use("java.net.URL");
    URL.$init.overload("java.lang.String").implementation = function (s) {
      try { report(s, "URL(String)"); } catch (e) { }
      return this.$init(s);
    };
    console.log("@@ hooked java.net.URL(String)");
  } catch (e) { console.log("@@ URL err " + S(e)); }

  try {
    var URI = Java.use("java.net.URI");
    URI.$init.overload("java.lang.String").implementation = function (s) {
      try { report(s, "URI(String)"); } catch (e) { }
      return this.$init(s);
    };
    console.log("@@ hooked java.net.URI(String)");
  } catch (e) { console.log("@@ URI err " + S(e)); }
});

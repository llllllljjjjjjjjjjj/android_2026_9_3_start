"use strict";
// dy 可读抓包 v4（终版）：从 client.Request 全量 dump 搜索请求
// 覆盖: method / url / host / path / 全部 header（含签名头）/ body / 加密标志位
var FILTER = /search|suggest|discover/i;
var seen = 0;

Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }

  var RB = Java.use("com.bytedance.retrofit2.RequestBuilder");
  var target = RB.build.overload("com.bytedance.retrofit2.ExpandCallback");

  target.implementation = function (cb) {
    var ret = target.call(this, cb);
    try {
      var path = S(ret.getPath());
      if (FILTER.test(path)) {
        seen++;
        var out = [];
        out.push("#### [" + seen + "] " + S(ret.getMethod()) + " " + S(ret.getUrl()));
        out.push("  host=" + S(ret.getHost()) + " path=" + S(ret.getPath()));
        out.push("  flags: queryEnc=" + S(ret.isQueryEncryptEnabled())
                 + " bodyEnc=" + S(ret.isBodyEncryptEnabled())
                 + " pureReq=" + S(ret.isPureRequest())
                 + " addCommon=" + S(ret.isAddCommonParam()));
        try {
          var hs = ret.getHeaders();
          if (hs) {
            for (var i = 0; i < hs.size(); i++) {
              var h = hs.get(i);
              try { out.push("  H " + S(h.getName()) + ": " + S(h.getValue())); }
              catch (e2) { out.push("  H(raw) " + S(h)); }
            }
          }
        } catch (e3) { out.push("  H_ERR " + S(e3)); }
        try {
          var b = ret.getBody();
          if (b) {
            out.push("  BODY mime=" + S(b.mimeType()) + " len=" + S(b.length()));
            try {
              var baos = Java.use("java.io.ByteArrayOutputStream").$new();
              b.writeTo(baos);
              var s = baos.toString("UTF-8");
              out.push("  BODY_TEXT " + S(s).slice(0, 800));
            } catch (e6) { out.push("  BODY_WRITE_ERR " + S(e6)); }
          }
        } catch (e4) {}
        console.log(out.join("\n"));
      }
    } catch (e) { console.log("DUMP_ERR " + S(e)); }
    return ret;
  };
  console.log("[*] hooked v4 (client.Request full dump)");
});

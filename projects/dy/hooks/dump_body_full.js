"use strict";
// 完整落盘搜索请求（body 不截断），用于判断公共参数位置
var FILTER = /search|suggest/i;
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
        out.push("@@@REQ[" + seen + "] " + S(ret.getMethod()) + " " + S(ret.getUrl()));
        out.push("@@@FLAGS queryEnc=" + S(ret.isQueryEncryptEnabled()) + " bodyEnc=" + S(ret.isBodyEncryptEnabled()) + " pure=" + S(ret.isPureRequest()));
        try {
          var b = ret.getBody();
          if (b) {
            var baos = Java.use("java.io.ByteArrayOutputStream").$new();
            b.writeTo(baos);
            var bodyStr = String(baos.toString("UTF-8"));
            out.push("@@@BODY_LEN " + bodyStr.length);
            out.push("@@@BODY_BEGIN");
            out.push(bodyStr);
            out.push("@@@BODY_END");
          }
        } catch (e) { out.push("@@@BODY_ERR " + S(e)); }
        console.log(out.join("\n"));
      }
    } catch (e) { console.log("@@@ERR " + S(e)); }
    return ret;
  };
  console.log("@@@ hooked full-body dump");
});

"use strict";
// 放宽条件抓完整 header map：size>=5 且含 >=3 个 x-/tt- 头
var dumped = 0;
var seenSizes = {};

Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }

  function looksLikeHeaders(m) {
    try {
      var n = m.size();
      if (n < 5 || seenSizes[n]) return false;
      // 用 JSONObject 转出来检查 key 特征
      var JO = Java.use("org.json.JSONObject");
      var txt = String(JO.$new(m).toString());
      var cnt = 0;
      var re = /"(x-[a-z0-9-]+|tt-[a-z0-9-]+|X-[A-Za-z0-9-]+)":/g;
      while (re.exec(txt) !== null) cnt++;
      if (cnt >= 3) {
        seenSizes[n] = true;
        dumped++;
        console.log("@@FULL[" + dumped + "] size=" + n + " xcount=" + cnt);
        console.log("@@JSON " + txt.slice(0, 6000));
        return true;
      }
    } catch (e) { }
    return false;
  }

  try {
    var HM = Java.use("java.util.HashMap");
    HM.put.implementation = function (k, v) {
      var r = this.put(k, v);
      try { if (this.size() >= 5) looksLikeHeaders(this); } catch (e) { }
      return r;
    };
  } catch (e) { }

  try {
    var LHM = Java.use("java.util.LinkedHashMap");
    LHM.put.implementation = function (k, v) {
      var r = this.put(k, v);
      try { if (this.size() >= 5) looksLikeHeaders(this); } catch (e) { }
      return r;
    };
  } catch (e) { }

  console.log("@@ hooked (relaxed header map capture)");
});

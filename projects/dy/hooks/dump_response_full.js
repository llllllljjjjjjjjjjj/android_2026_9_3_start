"use strict";
// 响应侧实证 v3：完整落盘 search 相关响应 + 记录下发字段名全集
var HIT = /search_id|search_session_id|related_search|realtime_feature|log_pb/i;
var respN = 0;
var fieldSet = {};

Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }

  var JT = Java.use("com.bytedance.aweme.coffee.json.JSONTokenerGetter");
  JT.get.implementation = function (s) {
    try {
      if (s && HIT.test(s)) {
        respN++;
        console.log("<<RESP[" + respN + "] len=" + s.length + ">>");
        console.log("FULL " + S(s).slice(0, 1200));
        // 收集响应顶层字段名
        var re = /"([a-z_]{3,40})"\s*:/g, m;
        while ((m = re.exec(s)) !== null) { fieldSet[m[1]] = (fieldSet[m[1]] || 0) + 1; }
      }
    } catch (e) {}
    return this.get(s);
  };
  console.log("[*] hooked v3 (full response dump)");

  rpc.exports = {
    fields: function () { return fieldSet; },
    count: function () { return respN; }
  };
});

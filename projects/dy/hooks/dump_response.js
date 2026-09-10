"use strict";
// 响应侧实证 + ClientKey 时机探测
var HIT = /search_id|search_session_id|related_search|realtime_feature/i;
var respN = 0;

Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }

  // 1) 响应解析入口：JSONTokenerGetter.get(String)
  try {
    var JT = Java.use("com.bytedance.aweme.coffee.json.JSONTokenerGetter");
    JT.get.implementation = function (s) {
      try {
        if (s && HIT.test(s)) {
          respN++;
          var out = ["<<RESP[" + respN + "] len=" + s.length + ">>"];
          var re = /"(search_id|search_session_id|related_search[^"]*|realtime_feature_channel)"\s*:\s*("?[^,}]{0,100})/gi;
          var m, n = 0;
          while ((m = re.exec(s)) !== null && n < 8) {
            out.push("   " + m[1] + " = " + m[2].replace(/\s+/g, " "));
            n++;
          }
          console.log(out.join("\n"));
        }
      } catch (e) {}
      return this.get(s);
    };
    console.log("[*] hooked JSONTokenerGetter.get");
  } catch (e) { console.log("JT err " + S(e)); }

  // 2) ClientKey 处理时机（签名链路实证）
  try {
    var M = Java.use("com.bytedance.retrofit2.RetrofitMetrics");
    M.addClientKeyStart.overloads.forEach(function (o) {
      o.implementation = function () {
        console.log("[metrics] addClientKeyStart");
        return o.call(this);
      };
    });
    M.addClientKeyEnd.overloads.forEach(function (o) {
      o.implementation = function () {
        console.log("[metrics] addClientKeyEnd");
        return o.call(this);
      };
    });
    console.log("[*] hooked RetrofitMetrics clientKey timing");
  } catch (e) { console.log("Metrics err " + S(e)); }
});

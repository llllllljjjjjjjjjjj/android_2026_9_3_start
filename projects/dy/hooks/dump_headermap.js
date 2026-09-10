"use strict";
// 在关键 header 被 put 的瞬间 dump 整个 header map（拿到完整请求头集合）
var TRIGGER = /^(x-tt-token|x-bd-client-key|x-ss-dp|x-tt-ext-info|bd-ticket-guard-key-sign)$/i;
var dumped = 0;

Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }

  function dumpMap(m, why) {
    try {
      var JO = Java.use("org.json.JSONObject");
      var jo = JO.$new(m);
      var txt = String(jo.toString());
      dumped++;
      console.log("@@HM[" + dumped + "] trigger=" + why + " size=" + m.size());
      console.log("@@HM_JSON " + txt.slice(0, 3000));
    } catch (e) { console.log("@@HM_ERR " + S(e)); }
  }

  try {
    var HM = Java.use("java.util.HashMap");
    HM.put.implementation = function (k, v) {
      var r = this.put(k, v);
      try {
        var ks = S(k);
        if (TRIGGER.test(ks)) {
          dumpMap(this, ks);
        }
      } catch (e) { }
      return r;
    };
    console.log("@@ hooked HashMap.put");
  } catch (e) { console.log("@@ HM hook err " + S(e)); }

  // LinkedHashMap 也可能被用
  try {
    var LHM = Java.use("java.util.LinkedHashMap");
    LHM.put.implementation = function (k, v) {
      var r = this.put(k, v);
      try {
        var ks = S(k);
        if (TRIGGER.test(ks)) { dumpMap(this, "LHM:" + ks); }
      } catch (e) { }
      return r;
    };
    console.log("@@ hooked LinkedHashMap.put");
  } catch (e) { }
});

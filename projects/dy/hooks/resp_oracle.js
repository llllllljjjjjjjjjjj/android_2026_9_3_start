"use strict";
// A 方案：App 自己发请求（参数/签名/会话全由 App 生成），RPC 取回真实响应
// 1) hook 响应解析入口，缓存含搜索结果的响应
// 2) RPC: list()/get(i)/clear()/count()
var RESP = [];
var MAX = 60;

Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }

  function keep(s) {
    if (!s || s.length < 40) return;
    // 只留含搜索业务特征的响应
    if (!/search_id|aweme_video|log_pb|global_doodle|data":\[|card_name|doc_dict/i.test(s)) return;
    if (RESP.length >= MAX) RESP.shift();
    RESP.push({ t: Date.now(), len: s.length, body: s });
  }

  try {
    var JT = Java.use("com.bytedance.aweme.coffee.json.JSONTokenerGetter");
    JT.get.implementation = function (s) {
      try { keep(S(s)); } catch (e) { }
      return this.get(s);
    };
    console.log("[*] hooked JSONTokenerGetter (response cache)");
  } catch (e) { console.log("JT err " + S(e)); }

  rpc.exports = {
    count: function () { return RESP.length; },
    list: function () {
      return RESP.map(function (r) { return { t: r.t, len: r.len, head: r.body.slice(0, 300) }; });
    },
    get: function (i) {
      var idx = (i < 0) ? RESP.length + i : i;
      var r = RESP[idx];
      return r ? { t: r.t, len: r.len, body: r.body } : null;
    },
    getlatest: function () {
      var r = RESP[RESP.length - 1];
      return r ? { t: r.t, len: r.len, body: r.body } : null;
    },
    find: function (kw) {
      var out = [];
      for (var i = 0; i < RESP.length; i++) {
        if (RESP[i].body.indexOf(kw) >= 0) out.push(i);
      }
      return out;
    },
    clear: function () { RESP = []; return 0; }
  };
  console.log("[*] rpc ready: count/list/get/getlatest/find/clear");
});

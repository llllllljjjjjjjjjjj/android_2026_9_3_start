// dy_hook88_url.js — 轻量全量 URL 捕获（内存缓存 + RPC，无落盘无 flush）
var reqs = [];
var MAX = 120;
var armed = false;

function arm() {
  if (armed) return;
  var m = Process.findModuleByName("libmetasec_ml.so");
  if (!m) return;
  try {
    Interceptor.attach(m.base.add(0x28065c), {
      onEnter: function (args) {
        try {
          var u = args[0].isNull() ? "" : args[0].readUtf8String();
          var h = args[1].isNull() ? "" : args[1].readUtf8String();
          if (!u) return;
          var rec = { url: u, headers: h, ts: Date.now() };
          reqs.push(rec);
          if (reqs.length > MAX) reqs.shift();
        } catch (e) {}
      }
    });
    armed = true;
    send({ t: "ready", m: "hook88 armed" });
  } catch (e) {
    send({ t: "err", m: e.message });
  }
}

arm();
setInterval(arm, 2000);

rpc.exports = {
  list: function () { return reqs; },
  find: function (sub) {
    var out = [];
    reqs.forEach(function (r) { if (!sub || r.url.indexOf(sub) >= 0) out.push(r); });
    return out;
  },
  tail: function (n) { n = n || 20; return reqs.slice(-n); }
};

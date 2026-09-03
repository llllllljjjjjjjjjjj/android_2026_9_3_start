// dy_hook91_allurl.js — 全量 URL 捕获（28065c + 47aaec 双点，内存缓存 + RPC）
var reqs = [];
var MAX = 200;
var armed1 = false;
var armed2 = false;

function push(u) {
  if (!u) return;
  reqs.push({ url: u, ts: Date.now() });
  if (reqs.length > MAX) reqs.shift();
}

function arm1() {
  if (armed1) return;
  var m = Process.findModuleByName("libmetasec_ml.so");
  if (!m) return;
  try {
    Interceptor.attach(m.base.add(0x28065c), {
      onEnter: function (args) {
        try { push(args[0].isNull() ? "" : args[0].readUtf8String()); } catch (e) {}
      }
    });
    armed1 = true;
  } catch (e) {}
}

function arm2() {
  if (armed2) return;
  var c = Process.findModuleByName("libsscronet.so");
  if (!c) return;
  try {
    Interceptor.attach(c.base.add(0x47aaec), {
      onEnter: function (args) {
        try {
          var x0 = this.context.x0;
          push(x0.isNull() ? "" : x0.readUtf8String());
        } catch (e) {}
      }
    });
    armed2 = true;
  } catch (e) {}
}

arm1();
arm2();
setInterval(function () { arm1(); arm2(); }, 2000);
send({ t: "ready", m: "hook91 loaded" });

rpc.exports = {
  tail: function (n) { n = n || 50; return reqs.slice(-n); },
  find: function (sub) {
    var out = [];
    reqs.forEach(function (r) { if (!sub || r.url.indexOf(sub) >= 0) out.push(r); });
    return out;
  }
};

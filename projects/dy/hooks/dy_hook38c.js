// dy_hook38c.js — 电商请求捕获（URL+headers+body，RPC 可取）
// 基于 hook38：28065c 抓 URL/headers，Cronet Read provider 回填 body。
// 过滤 product/detail/ecom 域名请求。
var MS = null;
var fnGetData = null;
var fnGetSize = null;
var reqs = [];
var MAX = 12;
var winMs = 15000;
var signArmed = false;
var readsArmed = false;

function armSign() {
  if (signArmed) return;
  var m = Process.findModuleByName("libmetasec_ml.so");
  if (!m) return;
  try {
    Interceptor.attach(m.base.add(0x28065c), {
      onEnter: function (args) {
        try {
          var u = args[0].isNull() ? "" : args[0].readUtf8String();
          if (!/product\/detail|ecom\/product|shop\/|commerce\//.test(u)) return;
          var h = args[1].isNull() ? "" : args[1].readUtf8String();
          reqs.push({ url: u, headers: h, bodyB64: "", size: 0, ts: Date.now() });
          if (reqs.length > MAX) reqs.shift();
          send({ t: "req", url: u.slice(0, 150) });
        } catch (e) {}
      }
    });
    signArmed = true;
    send({ t: "info", m: "ecom capture armed" });
  } catch (e) {
    send({ t: "err", m: "sign attach fail: " + e.message });
  }
}

function armReads() {
  if (readsArmed) return;
  var c = Process.findModuleByName("libsscronet.so");
  if (!c) return;
  c.enumerateExports().forEach(function (e) {
    if (e.name === "Cronet_Buffer_GetData") fnGetData = new NativeFunction(e.address, 'pointer', ['pointer']);
    if (e.name === "Cronet_Buffer_GetSize") fnGetSize = new NativeFunction(e.address, 'uint64', ['pointer']);
  });
  var done = 0;
  [0x27765c, 0x1ee748].forEach(function (off) {
    try {
      Interceptor.attach(c.base.add(off), {
        onEnter: function (args) { this.buf = args[2]; },
        onLeave: function () {
          try {
            if (Date.now() > Date.now() + 1) return;
            if (!this.buf || this.buf.isNull() || !fnGetData || !fnGetSize) return;
            var data = fnGetData(this.buf);
            var size = Number(fnGetSize(this.buf));
            if (data.isNull() || size < 4 || size > 524288) return;
            for (var i = reqs.length - 1; i >= 0; i--) {
              if (reqs[i].bodyB64 === "" && Date.now() - reqs[i].ts < winMs) {
                var bytes = data.readByteArray(size);
                if (bytes === null) return;
                var u8 = new Uint8Array(bytes);
                var bin = "";
                for (var j = 0; j < u8.length; j++) bin += String.fromCharCode(u8[j]);
                reqs[i].bodyB64 = btoa(bin);
                reqs[i].size = size;
                send({ t: "body", url: reqs[i].url.slice(0, 120), size: size });
                return;
              }
            }
          } catch (e) {}
        }
      });
      done++;
    } catch (e) {}
  });
  readsArmed = done > 0;
  if (readsArmed) send({ t: "info", m: "read capture armed (" + done + ")" });
}

setInterval(armSign, 1000);
setInterval(armReads, 1000);
armSign();
armReads();

rpc.exports = {
  list: function () { return reqs; },
  find: function (sub) {
    var out = [];
    reqs.forEach(function (r) { if (!sub || r.url.indexOf(sub) >= 0) out.push(r); });
    return out;
  },
  reset: function () { reqs = []; return "reset"; }
};
send({ t: "ready", m: "hook38c loaded" });

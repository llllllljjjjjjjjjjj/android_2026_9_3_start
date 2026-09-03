// dy_hook85_ecom_all.js — 电商链路全量请求捕获（URL + headers + body）
// 基于 hook38 机制：metasec+0x28065c 抓 URL/headers，Cronet Read provider 回填 body。
// 不设域名过滤（商品详情/产品参数/品牌资质可能走 amemv/ecommerce/ibuycott/douyinec 任意主机）。
// RPC: list() / find(substr) / reset()
var MS = null;
var fnGetData = null;
var fnGetSize = null;
var reqs = [];            // [{url, headers, bodyB64, size, ts}]
var MAX = 40;
var winMs = 30000;        // body 回填窗口（商品详情链多请求并发，放大到 30s）
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
          var h = args[1].isNull() ? "" : args[1].readUtf8String();
          if (!u) return;
          reqs.push({ url: u, headers: h, bodyB64: "", size: 0, ts: Date.now() });
          if (reqs.length > MAX) reqs.shift();
          send({ t: "req", url: u.slice(0, 200) });
        } catch (e) {}
      }
    });
    signArmed = true;
    send({ t: "info", m: "ecom sign capture armed (all urls)" });
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
            if (!this.buf || this.buf.isNull() || !fnGetData || !fnGetSize) return;
            var data = fnGetData(this.buf);
            var size = Number(fnGetSize(this.buf));
            if (data.isNull() || size < 4 || size > 1048576) return;
            // 回填最近一条未带 body 的请求（不限制域名）
            for (var i = reqs.length - 1; i >= 0; i--) {
              if (reqs[i].bodyB64 === "" && Date.now() - reqs[i].ts < winMs) {
                var bytes = data.readByteArray(size);
                if (bytes === null) return;
                var u8 = new Uint8Array(bytes);
                var bin = "";
                for (var j = 0; j < u8.length; j++) bin += String.fromCharCode(u8[j]);
                reqs[i].bodyB64 = btoa(bin);
                reqs[i].size = size;
                send({ t: "body", idx: i, url: reqs[i].url.slice(0, 120), size: size });
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
  if (readsArmed) send({ t: "info", m: "ecom read capture armed (" + done + ")" });
}

setInterval(armSign, 1000);
setInterval(armReads, 1000);
armSign();
armReads();

rpc.exports = {
  list: function () {
    return reqs;
  },
  find: function (sub) {
    var out = [];
    reqs.forEach(function (r) {
      if (!sub || r.url.indexOf(sub) >= 0 || (r.bodyB64 && atob(r.bodyB64).indexOf(sub) >= 0)) {
        out.push(r);
      }
    });
    return out;
  },
  reset: function () {
    reqs = [];
    return "reset";
  }
};
send({ t: "ready", m: "hook85 ecom loaded" });

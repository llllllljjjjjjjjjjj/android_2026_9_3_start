// dy_hook38_device_request.js v2 — 设备端完整搜索请求捕获 oracle（多请求缓存）
// 捕获 App 真机构建的搜索族请求（URL + headers 串 + body），RPC 可取最近 N 条。
// 参数全部由真机生成（x-tt-token/bd-ticket-guard/x-tt-dt/trace-id…），PC 端仅补八神。
var MS = null;
var fnGetData = null;
var fnGetSize = null;
var reqs = [];            // 最近请求列表 [{url, headers, bodyB64, size, ts}]
var MAX = 8;
var searchWin = 0;
var winMs = 8000;
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
          if (!/search|general|sug/.test(u)) return;
          var h = args[1].isNull() ? "" : args[1].readUtf8String();
          reqs.push({ url: u, headers: h, bodyB64: "", size: 0, ts: Date.now() });
          if (reqs.length > MAX) reqs.shift();
          searchWin = Date.now();
          send({ t: "req", url: u.slice(0, 130) });
        } catch (e) {}
      }
    });
    signArmed = true;
    send({ t: "info", m: "sign capture armed (once)" });
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
            if (Date.now() - searchWin > winMs) return;
            if (!this.buf || this.buf.isNull() || !fnGetData || !fnGetSize) return;
            var data = fnGetData(this.buf);
            var size = Number(fnGetSize(this.buf));
            if (data.isNull() || size < 4 || size > 262144) return;
            // 回填最近一条未带 body 的搜索请求
            for (var i = reqs.length - 1; i >= 0; i--) {
              if (reqs[i].bodyB64 === "" && Date.now() - reqs[i].ts < winMs) {
                var bytes = data.readByteArray(size);
                if (bytes === null) return;
                var u8 = new Uint8Array(bytes);
                var bin = "";
                for (var j = 0; j < u8.length; j++) bin += String.fromCharCode(u8[j]);
                reqs[i].bodyB64 = btoa(bin);
                reqs[i].size = size;
                send({ t: "body", idx: i, size: size });
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
  list: function () {
    return reqs;
  },
  mainsearch: function () {
    for (var i = reqs.length - 1; i >= 0; i--) {
      if (/general\/(stream|single)/.test(reqs[i].url)) return reqs[i];
    }
    return null;
  },
  reset: function () {
    reqs = [];
    return "reset";
  }
};
send({ t: "ready", m: "hook38v2 loaded" });

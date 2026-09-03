// dy_hook34_body_zstd.js — 搜索请求 body 全量捕获 v2（修重挂 bug + 双 Read 通道）
//
// 通道 A: libsscronet+0x27765c (Cronet_UploadDataProvider_Read 共享桩) —— 抓到过 HTTPDNS body
// 通道 B: libsscronet+0x1ee748 (provider vtable vt[0] Read) —— hook33 里 dump 到八神头串，
//         搜索 POST body 大概率也走这条（hook33 只 dump 前 128B 且无窗口，漏了压缩体）
// 触发窗口: metasec+0x28065c 签名命中 general/(single|stream)|sug 后 6s
// 输出: send({t:'body', ch:'A'|'B', size, b64})，PC 端解压解析
var MS = null;
var fnGetData = null;
var fnGetSize = null;
var searchWin = 0;
var winMs = 6000;
var signArmed = false;
var readArmed = { A: false, B: false };

function getBufFns(c) {
  if (fnGetData && fnGetSize) return true;
  c.enumerateExports().forEach(function (e) {
    if (e.name === "Cronet_Buffer_GetData") fnGetData = new NativeFunction(e.address, 'pointer', ['pointer']);
    if (e.name === "Cronet_Buffer_GetSize") fnGetSize = new NativeFunction(e.address, 'uint64', ['pointer']);
  });
  return !!(fnGetData && fnGetSize);
}

function attachRead(addr, ch) {
  try {
    Interceptor.attach(addr, {
      onEnter: function (args) { this.buf = args[2]; },
      onLeave: function () {
        try {
          if (Date.now() - searchWin > winMs || searchWin === 0) return;
          if (!this.buf || this.buf.isNull() || !fnGetData || !fnGetSize) return;
          var data = fnGetData(this.buf);
          var size = Number(fnGetSize(this.buf));
          if (data.isNull() || size < 4 || size > 262144) return;
          var bytes = data.readByteArray(size);
          if (bytes === null) return;
          var u8 = new Uint8Array(bytes);
          var bin = "";
          for (var i = 0; i < u8.length; i++) bin += String.fromCharCode(u8[i]);
          send({ t: "body", ch: ch, size: size, b64: btoa(bin) });
        } catch (e) {}
      }
    });
    return true;
  } catch (e) {
    return false;
  }
}

function armSign() {
  if (signArmed) return;
  var m = Process.findModuleByName("libmetasec_ml.so");
  if (!m) return;
  try {
    Interceptor.attach(m.base.add(0x28065c), {
      onEnter: function (args) {
        try {
          var u = args[0].isNull() ? "" : args[0].readUtf8String();
          if (!u) return;
          if (/general\/(single|stream)|search\/sug|search\/refresh_related_search/i.test(u)) {
            searchWin = Date.now();
            send({ t: "sign", url: u.slice(0, 160), ts: searchWin });
          }
        } catch (e) {}
      }
    });
    signArmed = true;
    send({ t: "info", m: "sign hook armed (once)" });
  } catch (e) {
    send({ t: "err", m: "sign attach fail: " + e.message });
  }
}

function armReads() {
  var c = Process.findModuleByName("libsscronet.so");
  if (!c) return;
  getBufFns(c);
  if (!readArmed.A) readArmed.A = attachRead(c.base.add(0x27765c), "A");
  if (!readArmed.B) readArmed.B = attachRead(c.base.add(0x1ee748), "B");
  if (readArmed.A || readArmed.B) {
    send({ t: "info", m: "read hooks A=" + readArmed.A + " B=" + readArmed.B });
  }
}

setInterval(armSign, 1000);
setInterval(armReads, 1000);
armSign();
armReads();
send({ t: "ready", m: "hook34v2 loaded" });

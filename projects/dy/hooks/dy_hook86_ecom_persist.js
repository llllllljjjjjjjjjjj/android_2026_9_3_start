// dy_hook86_ecom_persist.js — 电商链路全量捕获 + 设备端落盘（App 崩溃不丢）
// 基于 hook85：metasec+0x28065c 抓 URL/headers，Cronet Read provider 回填 body，
// 每条请求立即 append 写 /data/local/tmp/ecom_cap.jsonl（URL + headers + bodyB64）。
var FH_PATH = "/data/data/com.ss.android.ugc.aweme/files/ecom_cap.jsonl";
var fnGetData = null;
var fnGetSize = null;
var reqs = [];
var MAX = 60;
var winMs = 30000;
var fh = null;
var signArmed = false;
var readsArmed = false;

function openFh() {
  if (fh) return;
  try {
    var File = Java.use("java.io.File");
    var FOS = Java.use("java.io.FileOutputStream");
    var dir = File.$new("/data/local/tmp");
    if (!dir.exists()) dir.mkdirs();
    fh = FOS.$new(FH_PATH, true); // append
    console.log("[persist] file open ok");
  } catch (e) {
    console.log("[persist] open fail: " + e.message);
  }
}

function persist(rec) {
  try {
    if (!fh) return;
    var s = JSON.stringify(rec) + "\n";
    var Bytes = Java.use("[B");
    var jstr = Java.use("java.lang.String").$new(s);
    var bytes = jstr.getBytes("UTF-8");
    fh.write(bytes);
    fh.flush();
  } catch (e) {}
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
          var h = args[1].isNull() ? "" : args[1].readUtf8String();
          if (!u) return;
          var rec = { url: u, headers: h, bodyB64: "", size: 0, ts: Date.now() };
          reqs.push(rec);
          if (reqs.length > MAX) reqs.shift();
          persist(rec);
          send({ t: "req", url: u.slice(0, 180) });
        } catch (e) {}
      }
    });
    signArmed = true;
    send({ t: "info", m: "persist sign capture armed" });
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
            for (var i = reqs.length - 1; i >= 0; i--) {
              if (reqs[i].bodyB64 === "" && Date.now() - reqs[i].ts < winMs) {
                var bytes = data.readByteArray(size);
                if (bytes === null) return;
                var u8 = new Uint8Array(bytes);
                var bin = "";
                for (var j = 0; j < u8.length; j++) bin += String.fromCharCode(u8[j]);
                reqs[i].bodyB64 = btoa(bin);
                reqs[i].size = size;
                persist(reqs[i]);
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
  if (readsArmed) send({ t: "info", m: "persist read capture armed (" + done + ")" });
}

Java.perform(openFh);
setInterval(function () { Java.perform(openFh); armSign(); armReads(); }, 1000);
armSign();
armReads();

rpc.exports = {
  list: function () { return reqs; },
  find: function (sub) {
    var out = [];
    reqs.forEach(function (r) {
      if (!sub || r.url.indexOf(sub) >= 0) out.push(r);
    });
    return out;
  },
  reset: function () { reqs = []; return "reset"; }
};
send({ t: "ready", m: "hook86 persist loaded" });

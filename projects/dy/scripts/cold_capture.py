# -*- coding: utf-8 -*-
# cold_capture.py — 冷启动后抓 detail/stream 完整请求（URL + headers + body）
import subprocess
import sys
import time
from pathlib import Path

import frida

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"

JS = r'''
var fnGetData = null, fnGetSize = null;
var reqs = [];
var signArmed = false, readsArmed = false;

function armSign() {
  if (signArmed) return;
  var m = Process.findModuleByName("libmetasec_ml.so");
  if (!m) return;
  try {
    Interceptor.attach(m.base.add(0x28065c), {
      onEnter: function (args) {
        try {
          var u = args[0].isNull() ? "" : args[0].readUtf8String();
          if (!/product\/detail|ecom\/product/.test(u)) return;
          var h = args[1].isNull() ? "" : args[1].readUtf8String();
          reqs.push({ url: u, headers: h, bodyB64: "", ts: Date.now() });
          if (reqs.length > 20) reqs.shift();
          send({ t: "req", url: u.slice(0, 150) });
        } catch (e) {}
      }
    });
    signArmed = true;
    send({ t: "info", m: "sign armed" });
  } catch (e) { send({ t: "err", m: "sign: " + e.message }); }
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
            if (data.isNull() || size < 4 || size > 524288) return;
            for (var i = reqs.length - 1; i >= 0; i--) {
              if (reqs[i].bodyB64 === "" && Date.now() - reqs[i].ts < 15000) {
                var bytes = data.readByteArray(size);
                var u8 = new Uint8Array(bytes);
                var bin = "";
                for (var j = 0; j < u8.length; j++) bin += String.fromCharCode(u8[j]);
                reqs[i].bodyB64 = btoa(bin);
                send({ t: "body", url: reqs[i].url.slice(0, 100), size: size });
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
  send({ t: "info", m: "reads armed " + done });
}

setInterval(function () { armSign(); armReads(); }, 1000);
armSign(); armReads();
rpc.exports = { list: function () { return reqs; } };
'''

subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"],
                      stdout=subprocess.DEVNULL)
pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
sess = dev.attach(pid)
sc = sess.create_script(JS)

def on_msg(msg, data):
    p = msg.get("payload")
    if isinstance(p, dict):
        print(p.get("t"), p.get("url", p.get("m", "")), "size=" + str(p.get("size", "")), flush=True)

sc.on("message", on_msg)
sc.load()
print("挂载完成，打开详情页...", flush=True)
subprocess.check_call([ADB, "shell", "am", "start", "-a",
                       "android.intent.action.VIEW", "-d",
                       "https://v.douyin.com/c11KamCtyGw/"],
                      stdout=subprocess.DEVNULL)
time.sleep(20)
reqs = sc.exports_sync.list()
print("\n=== 捕获的请求 ===", flush=True)
for r in reqs:
    print(f"  url={r['url'][:120]}")
    print(f"  bodyB64_len={len(r['bodyB64'])}")
sess.detach()

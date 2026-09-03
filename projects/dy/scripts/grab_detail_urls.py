# -*- coding: utf-8 -*-
# grab_detail_urls.py — attach 短时抓 detail 相关接口完整 URL + headers（不抓 body）
import json
import subprocess
import sys
import time
from pathlib import Path

import frida

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
ROOT = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy")
OUT = ROOT / "capture" / "detail_reqs.jsonl"

JS = r'''
var armed = false;
function arm() {
  if (armed) return;
  var m = Process.findModuleByName("libmetasec_ml.so");
  if (!m) return;
  Interceptor.attach(m.base.add(0x28065c), {
    onEnter: function (args) {
      try {
        var u = args[0].isNull() ? "" : args[0].readUtf8String();
        if (!/ecom.*product|product.*detail/.test(u)) return;
        var h = args[1].isNull() ? "" : args[1].readUtf8String();
        send({ t: "req", url: u, headers: h });
      } catch (e) {}
    }
  });
  armed = true;
  send({ t: "ready" });
}
arm();
setInterval(arm, 1000);
'''

subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"],
                      stdout=subprocess.DEVNULL)
pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
sess = dev.attach(pid)
sc = sess.create_script(JS)

recs = []
def on_msg(msg, data):
    p = msg.get("payload")
    if isinstance(p, dict) and p.get("t") == "req":
        recs.append({"url": p["url"], "headers": p["headers"]})
        print("抓到:", p["url"][:120], flush=True)

sc.on("message", on_msg)
sc.load()
print("打开详情页触发请求...", flush=True)
subprocess.check_call([ADB, "shell", "am", "start", "-a",
                       "android.intent.action.VIEW", "-d",
                       "https://v.douyin.com/c11KamCtyGw/"],
                      stdout=subprocess.DEVNULL)
time.sleep(15)
sess.detach()

# 去重保存
seen = {}
for r in recs:
    key = r["url"].split("?")[0]
    if key not in seen:
        seen[key] = r
with open(OUT, "w", encoding="utf-8") as f:
    for r in seen.values():
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"\n保存 {len(seen)} 个接口 -> {OUT}")
for r in seen.values():
    print("  ", r["url"].split("?")[0])

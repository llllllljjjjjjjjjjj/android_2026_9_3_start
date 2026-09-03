# -*- coding: utf-8 -*-
# compare_shortlink.py — 抓短链跳转（网络异常）时的 detail 请求序列
import subprocess
import sys
import time
from pathlib import Path

import frida

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"

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
        if (u && /ecom|product|haohuo|jinritemai/.test(u)) {
          send({ t: "url", u: u.slice(0, 400) });
        }
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

urls = []
def on_msg(msg, data):
    p = msg.get("payload")
    if isinstance(p, dict) and p.get("t") == "url":
        u = p["u"]
        if u not in urls:
            urls.append(u)
            print("URL:", u.split("?")[0], "| 参数:", u.split("?")[1][:120] if "?" in u else "-", flush=True)

sc.on("message", on_msg)
sc.load()
print("已挂载，短链打开奥马...", flush=True)
subprocess.check_call([ADB, "shell", "am", "start", "-a",
                       "android.intent.action.VIEW", "-d",
                       "https://v.douyin.com/WulVH5sFMGk/"],
                      stdout=subprocess.DEVNULL)
time.sleep(18)
sess.detach()
print(f"\n共捕获 {len(urls)} 个电商 URL", flush=True)

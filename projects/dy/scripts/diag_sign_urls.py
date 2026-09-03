# -*- coding: utf-8 -*-
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
        if (u && /ecom|product|detail|shop|jinritemai|haohuo/.test(u)) {
          send({ t: "url", u: u.slice(0, 200) });
        }
      } catch (e) {}
    }
  });
  armed = true;
  send({ t: "ready", m: "armed" });
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

def on_msg(msg, data):
    p = msg.get("payload")
    if isinstance(p, dict):
        print(p.get("t"), p.get("u", p.get("m", "")), flush=True)

sc.on("message", on_msg)
sc.load()
print("已挂载，打开详情页触发请求...", flush=True)

subprocess.check_call([ADB, "shell", "am", "start", "-a",
                       "android.intent.action.VIEW", "-d",
                       "https://v.douyin.com/c11KamCtyGw/"],
                      stdout=subprocess.DEVNULL)
time.sleep(20)
sess.detach()

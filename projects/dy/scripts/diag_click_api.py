# -*- coding: utf-8 -*-
# diag_click_api.py — attach 短时抓「官方正品」点击是否触发 HTTP 接口
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
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
        if (u && u.indexOf("http") === 0) send({ t: "url", u: u.slice(0, 160) });
      } catch (e) {}
    }
  });
  armed = true;
  send({ t: "ready" });
}
arm();
setInterval(arm, 1000);
'''


def dump_ui():
    subprocess.run([ADB, "shell", "uiautomator", "dump", "/sdcard/ui.xml"],
                   capture_output=True, timeout=20)
    return subprocess.check_output([ADB, "shell", "cat", "/sdcard/ui.xml"]).decode(errors="replace")


def find_btn(xml, texts):
    try:
        root = ET.fromstring(xml)
    except Exception:
        return None
    for node in root.iter("node"):
        desc = node.get("content-desc") or ""
        txt = node.get("text") or ""
        for t in texts:
            if t in desc or t in txt:
                m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.get("bounds") or "")
                if m:
                    l, t_, r, b_ = map(int, m.groups())
                    return (l + r) // 2, (t_ + b_) // 2
    return None


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
            print("URL:", u, flush=True)

sc.on("message", on_msg)
sc.load()
print("已挂载，点击前先看现有页面...", flush=True)
time.sleep(2)

# 找「官方正品」按钮并点击
xml = dump_ui()
pt = find_btn(xml, ["官方正品", "官方品牌授权", "品牌官方授权"])
if not pt:
    subprocess.run([ADB, "shell", "input", "swipe", "540", "1700", "540", "600", "400"],
                   capture_output=True)
    time.sleep(2)
    xml = dump_ui()
    pt = find_btn(xml, ["官方正品", "官方品牌授权", "品牌官方授权"])
print("点击:", pt, flush=True)
if pt:
    subprocess.run([ADB, "shell", "input", "tap", str(pt[0]), str(pt[1])],
                   capture_output=True)
    time.sleep(10)
    print("\n=== 点击后新增 URL ===", flush=True)
    for u in urls:
        print(" ", u, flush=True)
sess.detach()

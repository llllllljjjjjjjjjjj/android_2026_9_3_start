# -*- coding: utf-8 -*-
# forge_spawn_run.py — spawn 注入 FORGE(含图片域名) + 自动走流程到授权查看器
import subprocess
import sys
import time

import frida

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
HOOK = r"D:\reserve_agent\ish-portable-kit\projects\dy\hooks\dy_hook30_img.js"

dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
pid = dev.spawn([PKG])
sess = dev.attach(pid)
src = open(HOOK, encoding="utf-8").read()
sc = sess.create_script(src)

def on_msg(m, d):
    p = m.get("payload") or {}
    if p.get("t") == "error":
        print("ERR", p, flush=True)

sc.on("message", on_msg)
sc.load()
dev.resume(pid)
print("spawned", pid, flush=True)
time.sleep(40)

# 打开详情页
subprocess.check_call([ADB, "shell", "am", "start", "-a", "android.intent.action.VIEW",
                       "-d", "https://v.douyin.com/c11KamCtyGw/"], stdout=subprocess.DEVNULL)
print("detail opening...", flush=True)
time.sleep(16)
# 滚动 → 弹层 → 授权查看器
subprocess.check_call([ADB, "shell", "input", "swipe", "540", "1500", "540", "1000", "400"])
time.sleep(2)
subprocess.check_call([ADB, "shell", "input", "swipe", "540", "1500", "540", "1000", "400"])
time.sleep(3)
subprocess.check_call([ADB, "shell", "input", "tap", "250", "1033"])
time.sleep(4)
subprocess.check_call([ADB, "shell", "input", "tap", "419", "1407"])
print("viewer tap done, waiting images load...", flush=True)
time.sleep(10)
try:
    print("forge stats:", sc.exports_sync.status(), flush=True)
except Exception as e:
    print("stats err", e, flush=True)
time.sleep(2)
sess.detach()
print("done", flush=True)

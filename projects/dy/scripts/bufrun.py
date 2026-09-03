# -*- coding: utf-8 -*-
# bufrun.py — 挂 hook101，重载详情页，收集 buffer dump
import subprocess
import sys
import time

import frida

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"

subprocess.check_call([ADB, "shell", "su", "-c", "rm -f /data/data/%s/files/bufdump.bin" % PKG],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
subprocess.check_call([ADB, "shell", "input", "keyevent", "4"], stdout=subprocess.DEVNULL)
time.sleep(2)

pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
print("pid", pid, flush=True)
dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
sess = dev.attach(pid)
src = open(r"D:\reserve_agent\ish-portable-kit\projects\dy\hooks\dy_hook101_alldump.js", encoding="utf-8").read()
sc = sess.create_script(src)
sc.load()
time.sleep(2)
print("hooked; opening detail...", flush=True)

subprocess.check_call([ADB, "shell", "am", "start", "-a", "android.intent.action.VIEW",
                       "-d", "https://v.douyin.com/c11KamCtyGw/"], stdout=subprocess.DEVNULL)
time.sleep(15)
try:
    sz = sc.exports_sync.size()
    print("bufdump size:", sz, flush=True)
except Exception as e:
    print("size err", e, flush=True)
time.sleep(3)
sess.detach()

# pull
subprocess.check_call([ADB, "shell", "su", "-c", "cp /data/data/%s/files/bufdump.bin /data/local/tmp/bufdump.bin && chmod 644 /data/local/tmp/bufdump.bin" % PKG])
subprocess.check_call([ADB, "pull", "/data/local/tmp/bufdump.bin",
                       r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\bufdump.bin"])
print("pulled", flush=True)

# -*- coding: utf-8 -*-
# hook30_hold.py — 轻量常驻 attach：加载 dy_hook30_probe.js（FORGE 证书绕过），保持连接
# 不 force-stop、不 swipe。用法: python hook30_hold.py [小时数，默认 8]
import io
import subprocess
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import frida

PKG = "com.ss.android.ugc.aweme"
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 8
HOOK = r"D:\reserve_agent\skills-portable-test\projects\dy\hooks\dy_hook30_probe.js"
ADB = r"D:\reserve_agent\skills-portable-test\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"

subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"])
dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
print(f"attach pid={pid}", flush=True)
sess = dev.attach(pid)

script = sess.create_script(open(HOOK, encoding="utf-8").read())
script.on("message", lambda m, d: print(str(m.get("payload", m))[:150], flush=True))
script.load()
print("hook30 loaded (FORGE=true), 常驻 %d 小时" % HOURS, flush=True)

t0 = time.time()
try:
    while time.time() - t0 < HOURS * 3600:
        time.sleep(5)
except KeyboardInterrupt:
    pass
print("detaching", flush=True)
sess.detach()

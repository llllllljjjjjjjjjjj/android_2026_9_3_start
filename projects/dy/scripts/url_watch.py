# -*- coding: utf-8 -*-
# url_watch.py — 持久 attach hook88，每秒 RPC tail 打印新 URL
import subprocess
import sys
import time
from pathlib import Path

import frida

ROOT = Path(__file__).resolve().parents[1]
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
OUT = ROOT / "capture" / "ecom_url_watch.log"

pid = int(subprocess.check_output([ADB, "shell", "pidof", "com.ss.android.ugc.aweme"]).decode().split()[0])
dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
sess = dev.attach(pid)
src = (ROOT / "hooks" / "dy_hook88_url.js").read_text(encoding="utf-8")
sc = sess.create_script(src)
sc.load()
print("hooked pid", pid, flush=True)

seen = set()
last = 0
try:
    while True:
        try:
            recs = sc.exports_sync.tail(40)
        except Exception:
            recs = []
        new = 0
        for r in recs:
            u = r.get("url", "")
            if u and u not in seen:
                seen.add(u)
                new += 1
                line = f"[URL] {u[:220]}"
                print(line, flush=True)
                with open(OUT, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
        time.sleep(1)
except KeyboardInterrupt:
    pass
sess.detach()

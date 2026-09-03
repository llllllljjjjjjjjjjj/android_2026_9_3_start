# -*- coding: utf-8 -*-
# authtext_run.py — 挂 hook97 扫授权文案上下文并提取 URL
import re
import subprocess
import sys
import time

import frida

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
OUT = r"D:\reserve_agent\ish-portable-kit\projects\dy\capture"

pid = int(subprocess.check_output([ADB, "shell", "pidof", "com.ss.android.ugc.aweme"]).decode().split()[0])
print("pid", pid, flush=True)
dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
sess = dev.attach(pid)
src = open(r"D:\reserve_agent\ish-portable-kit\projects\dy\hooks\dy_hook97_authtext.js", encoding="utf-8").read()
sc = sess.create_script(src)

URL_RE = re.compile(r'https?://[^"\s\\]{10,800}?\.(?:png|jpg|jpeg|webp|heic|gif)[^"\s\\]*')
idx = {"n": 0}

def on_msg(m, d):
    p = m.get("payload") or {}
    if p.get("t") == "ctx":
        idx["n"] += 1
        body = p["body"]
        fn = rf"{OUT}\authtext_{idx['n']:02d}.json"
        with open(fn, "w", encoding="utf-8", errors="replace") as f:
            f.write(body)
        urls = URL_RE.findall(body)
        print(f"[{idx['n']}] addr={p['addr']} len={len(body)} urls={len(urls)}", flush=True)
        for u in urls[:12]:
            print("   ", u[:180], flush=True)

sc.on("message", on_msg)
sc.load()
time.sleep(1)
res = sc.exports_sync.scan()
print("ctx dumped:", res, flush=True)
sess.detach()

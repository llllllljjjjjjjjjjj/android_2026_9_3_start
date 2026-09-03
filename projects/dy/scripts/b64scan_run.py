# -*- coding: utf-8 -*-
# b64scan_run.py — 挂 hook99 扫 base64 图并落盘
import subprocess
import sys
import time

import frida

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
OUT = r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\b64"

pid = int(subprocess.check_output([ADB, "shell", "pidof", "com.ss.android.ugc.aweme"]).decode().split()[0])
print("pid", pid, flush=True)
dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
sess = dev.attach(pid)
src = open(r"D:\reserve_agent\ish-portable-kit\projects\dy\hooks\dy_hook99_b64.js", encoding="utf-8").read()
sc = sess.create_script(src)

idx = {"n": 0}

def on_msg(m, d):
    p = m.get("payload") or {}
    if p.get("t") == "b64":
        idx["n"] += 1
        import pathlib
        pathlib.Path(OUT).mkdir(exist_ok=True)
        fn = rf"{OUT}\b64_{idx['n']:02d}_{p['addr']}.txt"
        with open(fn, "w", encoding="utf-8", errors="replace") as f:
            f.write(p["body"])
        print(f"DUMP #{idx['n']} -> {fn} ({len(p['body'])}B)", flush=True)

sc.on("message", on_msg)
sc.load()
time.sleep(1)
res = sc.exports_sync.scan()
print("hits:", res, flush=True)
sess.detach()

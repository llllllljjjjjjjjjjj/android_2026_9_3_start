# -*- coding: utf-8 -*-
# qualbig_run.py — 挂 hook93，落盘大窗口 qualification JSON，扫描完成后退出
import subprocess
import sys
import time
from pathlib import Path

import frida

ROOT = Path(__file__).resolve().parents[1]
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
OUT = ROOT / "capture" / "qualbig"
OUT.mkdir(exist_ok=True)

pid = int(subprocess.check_output([ADB, "shell", "pidof", "com.ss.android.ugc.aweme"]).decode().split()[0])
dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
sess = dev.attach(pid)
src = (ROOT / "hooks" / "dy_hook93_qualbig.js").read_text(encoding="utf-8")
sc = sess.create_script(src)

count = {"n": 0}

def on_msg(msg, data):
    p = msg.get("payload") or {}
    t = p.get("t")
    if t == "qual":
        count["n"] += 1
        fn = OUT / f"qual_{count['n']:02d}_{p.get('addr','x')}.json"
        fn.write_text(p["body"], encoding="utf-8", errors="replace")
        print(f"DUMP #{count['n']} -> {fn.name} ({len(p['body'])}B)", flush=True)
    elif t == "done":
        print("scan done:", p.get("n"), flush=True)

sc.on("message", on_msg)
sc.load()
time.sleep(1)
sc.exports_sync.scan()
# 等消息回传
time.sleep(8)
print("total dumped:", count["n"], flush=True)
sess.detach()

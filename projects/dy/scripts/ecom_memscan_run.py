# -*- coding: utf-8 -*-
# ecom_memscan_run.py — 挂 hook86(请求落盘) + hook87(内存扫描) ，JSON 片段落盘
# 用法: python ecom_memscan_run.py [duration_sec]
import sys
import time
from pathlib import Path

import frida

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "hooks"
OUT = ROOT / "capture" / "memscan_json"
OUT.mkdir(exist_ok=True)
DUR = int(sys.argv[1]) if len(sys.argv) > 1 else 300

import subprocess

ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
pid = int(subprocess.check_output([ADB, "shell", "pidof", "com.ss.android.ugc.aweme"]).decode().split()[0])
print("attach pid", pid)

dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
sess = dev.attach(pid)
scripts = []
for name in ("dy_hook86_ecom_persist.js", "dy_hook87_memscan.js"):
    src = (HOOKS / name).read_text(encoding="utf-8")
    scripts.append(sess.create_script(src))

count = {"json": 0, "req": 0}

def on_msg(msg, data):
    p = msg.get("payload")
    if isinstance(p, dict):
        t = p.get("t")
        if t == "json":
            count["json"] += 1
            fn = OUT / f"json_{count['json']:03d}.txt"
            fn.write_text(p["body"], encoding="utf-8", errors="replace")
            print(f"[JSON] #{count['json']} addr={p.get('addr')} -> {fn.name} ({len(p['body'])}B)")
        elif t == "req":
            count["req"] += 1
            u = p.get("url", "")
            if "ecom" in u or "mall" in u or "product" in u or "brand" in u or "qualif" in u:
                print("[REQ]", u[:160])
        elif t == "body":
            print("[BODY]", p.get("url", "")[:120], p.get("size"))

for s in scripts:
    s.on("message", on_msg)
    s.load()
print("hooks loaded, scanning...")
end = time.time() + DUR
try:
    while time.time() < end:
        time.sleep(1)
except KeyboardInterrupt:
    pass
print(f"done: json={count['json']} req={count['req']}")
sess.detach()

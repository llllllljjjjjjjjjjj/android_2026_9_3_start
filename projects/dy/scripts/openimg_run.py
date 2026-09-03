# -*- coding: utf-8 -*-
# openimg_run.py — 挂 hook100 + 重新加载详情页 + 扫 open_image 上下文
import re
import subprocess
import sys
import time
from pathlib import Path

import frida

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
OUT = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\openimg")
OUT.mkdir(exist_ok=True)

# 触发详情页重新加载（BACK + 短链）
subprocess.check_call([ADB, "shell", "input", "keyevent", "4"], stdout=subprocess.DEVNULL)
time.sleep(2)

pid = int(subprocess.check_output([ADB, "shell", "pidof", "com.ss.android.ugc.aweme"]).decode().split()[0])
dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
sess = dev.attach(pid)
src = open(r"D:\reserve_agent\ish-portable-kit\projects\dy\hooks\dy_hook100_openimg.js", encoding="utf-8").read()
sc = sess.create_script(src)

idx = {"n": 0}
URL_RE = re.compile(r'https?://[^"\s\\]{10,900}?\.(?:png|jpg|jpeg|webp|heic|gif)[^"\s\\]*')

def on_msg(m, d):
    p = m.get("payload") or {}
    if p.get("t") == "ctx":
        idx["n"] += 1
        body = p["body"]
        fn = OUT / f"ctx_{idx['n']:02d}.json"
        fn.write_text(body, encoding="utf-8", errors="replace")
        urls = URL_RE.findall(body)
        print(f"[{idx['n']}] {p['addr']} len={len(body)} urls={len(urls)}", flush=True)
        for u in urls[:10]:
            print("   ", u[:180], flush=True)

sc.on("message", on_msg)
sc.load()
time.sleep(1)

# 触发详情页加载
subprocess.check_call([ADB, "shell", "am", "start", "-a", "android.intent.action.VIEW",
                       "-d", "https://v.douyin.com/c11KamCtyGw/"], stdout=subprocess.DEVNULL)
time.sleep(12)
res = sc.exports_sync.scan()
print("ctx dumped:", res, flush=True)
sess.detach()

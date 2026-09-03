# -*- coding: utf-8 -*-
# spawn_grab_stream.py — spawn App + 挂 hook88，冷启动后开短链抓 detail/stream 全量请求
import json
import subprocess
import sys
import time

import frida

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
OUT = r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\detail_stream_req.json"

subprocess.check_call([ADB, "shell", "am", "force-stop", "com.ss.android.ugc.aweme"])
time.sleep(3)

dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
pid = dev.spawn(["com.ss.android.ugc.aweme"])
sess = dev.attach(pid)
src = open(r"D:\reserve_agent\ish-portable-kit\projects\dy\hooks\dy_hook88_url.js", encoding="utf-8").read()
sc = sess.create_script(src)
sc.load()
dev.resume(pid)
print("spawned", pid, flush=True)

time.sleep(40)  # 等冷启动完成
subprocess.check_call([ADB, "shell", "am", "start", "-a", "android.intent.action.VIEW",
                       "-d", "https://v.douyin.com/c11KamCtyGw/"], stdout=subprocess.DEVNULL)

found = None
for _ in range(60):
    try:
        recs = sc.exports_sync.find("product/detail")
        for r in recs:
            u = r.get("url", "")
            if "product/detail/stream" in u:
                found = r
                break
    except Exception:
        pass
    if found:
        break
    time.sleep(1)

if found:
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(found, f, ensure_ascii=False, indent=2)
    print("SAVED", OUT, flush=True)
    print("url_len:", len(found["url"]), "headers_len:", len(found.get("headers", "")), flush=True)
else:
    print("stream not found", flush=True)
sess.detach()

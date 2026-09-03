# -*- coding: utf-8 -*-
# grab_detail_req.py — 挂 hook88 抓 detail/stream 完整请求 URL + headers
import subprocess
import sys
import time

import frida

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
OUT = r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\detail_stream_req.json"

pid = int(subprocess.check_output([ADB, "shell", "pidof", "com.ss.android.ugc.aweme"]).decode().split()[0])
dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
sess = dev.attach(pid)
src = open(r"D:\reserve_agent\ish-portable-kit\projects\dy\hooks\dy_hook88_url.js", encoding="utf-8").read()
sc = sess.create_script(src)
sc.load()
print("hooked", pid, flush=True)

found = None
for _ in range(60):
    try:
        recs = sc.exports_sync.find("product/detail")
        for r in recs:
            u = r.get("url", "")
            if "product/detail/stream" in u and len(u) > 300:
                found = r
                break
    except Exception:
        pass
    if found:
        break
    time.sleep(1)

if found:
    import json

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(found, f, ensure_ascii=False, indent=2)
    print("saved:", OUT, flush=True)
    print("url_len:", len(found["url"]), "headers_len:", len(found.get("headers", "")), flush=True)
else:
    print("not captured yet", flush=True)
sess.detach()

# -*- coding: utf-8 -*-
# test_oracle_real.py — 用真实 detail 请求参数测试八神 oracle 签名
import json
import subprocess
import sys
import time
from pathlib import Path

import frida

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
ROOT = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy")
HOOK = ROOT / "hooks" / "dy_hook21.js"

tmpl = json.loads((ROOT / "capture" / "detail_stream_req.json").read_text(encoding="utf-8"))
url = tmpl["url"]
hs = tmpl["headers"]
print("url len", len(url), "headers len", len(hs))

subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"],
                      stdout=subprocess.DEVNULL)
pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
sess = dev.attach(pid)
sc = sess.create_script(HOOK.read_text(encoding="utf-8"))
sc.load()
time.sleep(1)

out = sc.exports_sync.oracle(url, hs)
print("oracle raw:", repr(out)[:200] if out else "NULL/None")
if out:
    for line in out.split():
        if line.startswith("x-"):
            print("  ", line[:60])
sess.detach()

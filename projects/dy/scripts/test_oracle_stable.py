# -*- coding: utf-8 -*-
# test_oracle_stable.py — 验证八神签名 RPC oracle 稳定性（attach + 纯 RPC，无内存扫描）
import subprocess
import sys
import time
from pathlib import Path

import frida

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
HOOK = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\hooks\dy_hook21.js")

subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"],
                      stdout=subprocess.DEVNULL)
pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
print("attach pid", pid)
dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
sess = dev.attach(pid)
sc = sess.create_script(HOOK.read_text(encoding="utf-8"))
sc.load()
time.sleep(1)

url = "https://ecom.ecombdapi.com/ecom/product/detail/stream/?a=1"
hs = "cookie\r\na\r\nb\r\naccept-encoding\r\ngzip, deflate, br"
for i in range(3):
    try:
        out = sc.exports_sync.oracle(url, hs)
        print(f"[{i}] oracle ok, keys:", [l for l in out.split() if l.startswith("x-")][:6])
    except Exception as e:
        print(f"[{i}] oracle FAIL:", e)
    time.sleep(1)

# 观察 60s 是否崩
print("观察 60s 稳定性...")
for i in range(12):
    time.sleep(5)
    alive = subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().strip()
    if str(pid) not in alive.split():
        print(f"[{(i+1)*5}s] APP DEAD -> {alive}")
        sys.exit(1)
print("60s 稳定，纯 RPC oracle 可用")
sess.detach()

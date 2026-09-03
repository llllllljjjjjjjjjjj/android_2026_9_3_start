# -*- coding: utf-8 -*-
import subprocess
import sys
import time
import frida

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"

subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"],
                      stdout=subprocess.DEVNULL)
pid0 = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
print("attach pid", pid0)
dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
sess = dev.attach(pid0)
print("attached, no hook, observing 100s...")
for i in range(20):
    time.sleep(5)
    try:
        alive = subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().strip()
    except subprocess.CalledProcessError:
        alive = ""
    if str(pid0) not in alive.split():
        print(f"[{ (i+1)*5 }s] APP DEAD (pid {pid0} -> {alive or 'none'})")
        sys.exit(0)
    else:
        print(f"[{ (i+1)*5 }s] alive")
print("100s alive, pure attach does NOT kill")
sess.detach()

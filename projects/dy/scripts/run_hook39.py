# -*- coding: utf-8 -*-
# run_hook39.py — Python 挂 hook39 zstd 解码路径探针
import subprocess
import sys
import time
from pathlib import Path

import frida

ROOT = Path(__file__).resolve().parents[1]
ADB = r"D:\reserve_agent\skills-portable-test\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
HOOK = ROOT / "hooks" / "dy_hook39_zstd_probe.js"


def main():
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"])
    pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
    print("[*] attach pid=%d" % pid, flush=True)
    dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
    s = dev.attach(pid)
    sc = s.create_script(open(HOOK, encoding="utf-8").read())

    def on_msg(msg, data):
        if msg.get("type") == "log":
            print(msg.get("payload", ""), flush=True)
        elif msg.get("type") == "error":
            print("[JS-ERR]", msg.get("description"), flush=True)

    sc.on("message", on_msg)
    sc.load()
    print("[*] hook39 已挂载 —— %ds 内触发搜索" % duration, flush=True)
    time.sleep(duration)
    s.detach()


if __name__ == "__main__":
    main()

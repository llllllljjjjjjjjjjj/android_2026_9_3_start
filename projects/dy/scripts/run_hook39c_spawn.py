# -*- coding: utf-8 -*-
# run_hook39c_spawn.py — spawn 模式挂 zstd 启动探针（抓字典加载），期间触发搜索
import subprocess
import sys
import time
from pathlib import Path

import frida

ROOT = Path(__file__).resolve().parents[1]
ADB = r"D:\reserve_agent\skills-portable-test\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
HOOK = ROOT / "hooks" / "dy_hook39c_zstd_startup.js"


def main():
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"])
    dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
    print("[*] spawning %s ..." % PKG, flush=True)
    pid = dev.spawn([PKG])
    s = dev.attach(pid)
    sc = s.create_script(open(HOOK, encoding="utf-8").read())

    def on_msg(msg, data):
        if msg.get("type") == "log":
            print(msg.get("payload", ""), flush=True)
        elif msg.get("type") == "error":
            print("[JS-ERR]", msg.get("description"), flush=True)

    sc.on("message", on_msg)
    sc.load()
    dev.resume(pid)
    print("[*] spawned pid=%d resumed —— 观察 %ds（冷启动后自动触发搜索）" % (pid, duration), flush=True)
    # 120s 后自动触发一次搜索
    time.sleep(120)
    subprocess.check_call([ADB, "shell", "am", "start", "-a", "android.intent.action.VIEW",
                           "-d", "snssdk1128://search?keyword=%E7%BE%8E%E9%A3%9F"])
    print("[*] search triggered", flush=True)
    time.sleep(duration - 120)
    s.detach()


if __name__ == "__main__":
    main()

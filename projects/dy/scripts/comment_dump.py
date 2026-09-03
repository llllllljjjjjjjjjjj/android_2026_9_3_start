# -*- coding: utf-8 -*-
# comment_dump.py — attach 已运行的抖音，hook 28065c 收评论请求 URL+headers
# 用法: python comment_dump.py [秒数]   （默认 240s，期间手动刷评论区）
import sys
import time
import frida
import subprocess

ADB = r"D:\reserve_agent\skills-portable-test\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
HOOK = r"D:\reserve_agent\skills-portable-test\projects\dy\hooks\dy_hook31_comment_dump.js"
OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\capture\comment_dump.log"

def main():
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 240

    subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"])
    pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
    print("[*] attach pid=%d" % pid, flush=True)

    dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
    session = dev.attach(pid)
    script = session.create_script(open(HOOK, encoding="utf-8").read())

    logf = open(OUT, "w", encoding="utf-8")

    def on_msg(msg, data):
        if msg.get("type") == "log":
            line = msg.get("payload", "")
            print(line, flush=True)
            logf.write(line + "\n")
            logf.flush()
        elif msg.get("type") == "error":
            print("[JS-ERR]", msg.get("description"), flush=True)

    script.on("message", on_msg)
    script.load()
    print("[*] hook31 已挂载 —— 请在 %ds 内打开视频评论区并刷评论（含翻页）" % duration, flush=True)
    time.sleep(duration)
    print("[*] 时间到, 日志 → %s" % OUT, flush=True)
    session.detach()
    logf.close()

if __name__ == "__main__":
    main()

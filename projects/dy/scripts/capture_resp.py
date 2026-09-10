# -*- coding: utf-8 -*-
"""抓 libttboringssl SSL_read 的响应明文，落盘为二进制流
用法: python capture_resp.py <seconds> [keyword]
"""
import sys, time, subprocess, os
import frida

HOST = "127.0.0.1:27042"
JS = r"D:\reserve_agent\android\projects\dy\hooks\capture_resp.js"
PKG = "com.ss.android.ugc.aweme"
ADB = r"D:\reserve_agent\android\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
SERIAL = "9C181EC3BF7E0D"
OUT = r"D:\reserve_agent\android\projects\dy\capture\resp_stream.bin"


def adb(*a, timeout=30):
    return subprocess.run([ADB, "-s", SERIAL] + list(a), capture_output=True, text=True, timeout=timeout)


def main():
    secs = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    kw = sys.argv[2] if len(sys.argv) > 2 else None

    dev = frida.get_device_manager().add_remote_device(HOST)
    pid = (adb("shell", "pidof", PKG).stdout or "").strip().split()
    session = dev.attach(int(pid[0])) if pid else dev.attach(PKG)
    script = session.create_script(open(JS, encoding="utf-8").read())

    fh = open(OUT, "wb")
    total = 0

    def on_msg(m, data):
        nonlocal total
        if m.get("type") == "send" and data:
            fh.write(bytes(data))
            total += len(data)

    script.on("message", on_msg)
    script.load()
    print(f"[*] capturing {secs}s -> {OUT}")

    if kw:
        time.sleep(1)
        adb("shell", "am", "start", "-a", "android.intent.action.VIEW",
            "-d", f"snssdk1128://search?keyword={kw}")
        print(f"[*] search triggered: {kw}")

    time.sleep(secs)
    fh.close()
    session.detach()
    print(f"[*] done, {total} bytes captured")


if __name__ == "__main__":
    main()

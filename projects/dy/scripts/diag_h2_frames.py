# -*- coding: utf-8 -*-
"""诊断 SSL_write 抓到的原始帧结构"""
import sys, time, subprocess, os
import frida

HOST = "127.0.0.1:27042"
JS = r"D:\reserve_agent\android\projects\dy\hooks\cap_h2_headers.js"
PKG = "com.ss.android.ugc.aweme"
ADB = r"D:\reserve_agent\android\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
SERIAL = "9C181EC3BF7E0D"
AID = "7581630849533316401"


def adb(*a, timeout=30):
    return subprocess.run([ADB, "-s", SERIAL] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="ignore", timeout=timeout)


dev = frida.get_device_manager().add_remote_device(HOST)
pid = (adb("shell", "pidof", PKG).stdout or "").strip().split()
session = dev.attach(int(pid[0]))
sc = session.create_script(open(JS, encoding="utf-8").read())
frames = []


def on_msg(m, data):
    if m.get("type") == "send" and data:
        frames.append((m.get("payload", {}), bytes(data)))


sc.on("message", on_msg)
sc.load()
time.sleep(2)

adb("shell", "am", "start", "-a", "android.intent.action.VIEW",
    "-d", f"snssdk1128://aweme/detail/{AID}")
time.sleep(8)
session.detach()

print(f"frames: {len(frames)}")
for meta, d in frames[:12]:
    print(f"  n={meta.get('n')} len={meta.get('len')} "
          f"b0-4={meta.get('b0'):02x} {meta.get('b1'):02x} {meta.get('b2'):02x} "
          f"{meta.get('b3'):02x} {meta.get('b4'):02x}")
    print(f"    head32: {d[:32].hex()}")
    print(f"    ascii : {''.join(chr(b) if 32 <= b < 127 else '.' for b in d[:64])}")

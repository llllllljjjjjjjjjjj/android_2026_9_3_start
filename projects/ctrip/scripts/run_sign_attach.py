import time, frida, sys

PKG = "ctrip.android.view"
SCRIPT = r"D:\reserve_agent\ish-portable-kit\projects\ctrip\hooks\capture_sign.js"
LOGFILE = r"D:\reserve_agent\ish-portable-kit\projects\ctrip\capture\sign_capture.log"

code = open(SCRIPT, encoding="utf-8").read()

def on_message(msg, data):
    line = "[JS] " + str(msg.get("payload") if msg.get("type") == "send" else msg)
    print(line, flush=True)
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

import os, subprocess
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
# ensure adb server up + forward established (inherit stdio to avoid pipe EPERM)
os.system(f'"{ADB}" start-server >nul 2>&1')
os.system(f'"{ADB}" forward tcp:27042 tcp:27042 >nul 2>&1')
time.sleep(1)

device = frida.get_device_manager().add_remote_device("127.0.0.1:27042")

# find pid (adb pidof fallback pattern)
pid = None
try:
    for p in device.enumerate_processes():
        if p.name == PKG or p.pid and PKG in (p.name or ""):
            pid = p.pid
            break
except Exception as e:
    print("[!] enumerate failed:", e, flush=True)

if pid is None:
    print("[*] no running process; trying attach by name", flush=True)
    session = device.attach(PKG)
else:
    print("[*] attaching pid", pid, flush=True)
    session = device.attach(pid)

script = session.create_script(code)
script.on("message", on_message)
script.load()
print("[*] hook loaded", flush=True)
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("[*] stopped", flush=True)

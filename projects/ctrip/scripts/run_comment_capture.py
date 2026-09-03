import os, sys, time, frida

PKG = "ctrip.android.view"
SCRIPT = r"D:\reserve_agent\ish-portable-kit\projects\ctrip\hooks\capture_comment_request.js"
LOGFILE = r"D:\reserve_agent\ish-portable-kit\projects\ctrip\capture\comment_request.log"
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"

os.system(f'"{ADB}" start-server >nul 2>&1')
os.system(f'"{ADB}" forward tcp:27042 tcp:27042 >nul 2>&1')
time.sleep(1)

def on_msg(msg, data):
    line = "[JS] " + str(msg.get("payload") if msg.get("type") == "send" else msg)
    print(line, flush=True)
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

device = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
pid = device.spawn([PKG])
session = device.attach(pid)
script = session.create_script(open(SCRIPT, encoding="utf-8").read())
script.on("message", on_msg)
script.load()
device.resume(pid)
print("[*] spawned pid", pid, "hook loaded", flush=True)
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("[*] stopped", flush=True)

import sys, time, frida

PKG = "ctrip.android.view"
SCRIPT_PATH = r"D:\reserve_agent\ish-portable-kit\projects\ctrip\hooks\capture_review_api.js"
LOGFILE = r"D:\reserve_agent\ish-portable-kit\projects\ctrip\capture\review_api_capture.log"

with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
    code = f.read()

def on_message(msg, data):
    if msg.get("type") == "send":
        line = "[JS] " + str(msg.get("payload"))
    elif msg.get("type") == "error":
        line = "[JS-ERR] " + str(msg.get("stack", msg.get("description")))
    else:
        line = "[JS] " + str(msg)
    print(line, flush=True)
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

device = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
print("[*] spawning", PKG, flush=True)
pid = device.spawn([PKG])
session = device.attach(pid)
script = session.create_script(code)
script.on("message", on_message)
script.load()
device.resume(pid)
print("[*] resumed, pid", pid, flush=True)
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("[*] stopped", flush=True)

# 抖音八神 attach runner v2: 不重启 App, 直接 pidof + attach (App 需已在运行)
import frida
import sys
import time
import io
import subprocess

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PKG = "com.ss.android.ugc.aweme"
DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 180
HOOK = sys.argv[2] if len(sys.argv) > 2 else r"D:\reserve_agent\skills-portable-test\projects\dy\hooks\dy_hook12.js"
OUT = sys.argv[3] if len(sys.argv) > 3 else r"D:\reserve_agent\skills-portable-test\projects\dy\capture\dy_hook12_attach.log"
ADB = r"D:\reserve_agent\skills-portable-test\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"

outf = open(OUT, "w", encoding="utf-8")
t0 = time.time()

def log(line):
    outf.write(f"[{time.time()-t0:7.2f}] {line}\n")
    outf.flush()
    print(line, flush=True)

def on_message(msg, data):
    if msg["type"] == "error":
        log("JS-ERROR: " + str(msg.get("description"))[:2000])
    else:
        log(str(msg.get("payload")))

dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
sess = None
for i in range(10):
    r = subprocess.run([ADB, "shell", "pidof", PKG], capture_output=True, text=True)
    pids = r.stdout.strip().split()
    if not pids:
        log(f"pidof empty (try {i})")
        time.sleep(3)
        continue
    pid = int(pids[0])
    log(f"attaching pid={pid}")
    try:
        sess = dev.attach(pid)
        break
    except Exception as e:
        log(f"attach pid={pid} err: {e}")
        time.sleep(3)
if not sess:
    log("FAIL: app not found")
    outf.close()
    sys.exit(1)

script = sess.create_script(open(HOOK, encoding="utf-8").read())
script.on("message", on_message)
script.load()
log("script loaded (attach2 mode)")

try:
    while time.time() - t0 < DURATION:
        time.sleep(1)
except KeyboardInterrupt:
    pass
log("done, detaching")
try:
    sess.detach()
except Exception as e:
    log("detach err: " + str(e))
outf.close()

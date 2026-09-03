# 抖音八神动态抓取 runner (attach 版): 裸启动 App 后 attach + 加载 hook
import frida
import sys
import time
import io
import subprocess

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PKG = "com.ss.android.ugc.aweme"
DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 300
HOOK = sys.argv[2] if len(sys.argv) > 2 else r"D:\reserve_agent\skills-portable-test\projects\dy\hooks\dy_hook10.js"
OUT = sys.argv[3] if len(sys.argv) > 3 else r"D:\reserve_agent\skills-portable-test\projects\dy\capture\dy_hook_attach_out.log"
WAIT = int(sys.argv[4]) if len(sys.argv) > 4 else 45
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

# 1) 裸启动 App
subprocess.run([ADB, "shell", "am", "force-stop", PKG], capture_output=True)
time.sleep(2)
subprocess.run([ADB, "shell", "am", "start", "-n", PKG + "/.splash.SplashActivity"], capture_output=True)
log(f"bare-launched, waiting {WAIT}s ...")
time.sleep(WAIT)

# 2) attach: App 隐藏 /proc 条目 (frida 枚举不可见), 用 adb pidof 拿 pid
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
log("script loaded (attach mode)")

# 刺激流量: 每 10s 上滑 feed
import threading
def swipe_loop():
    while True:
        subprocess.run([ADB, "shell", "input", "swipe", "540", "1600", "540", "600", "200"], capture_output=True)
        time.sleep(10)
threading.Thread(target=swipe_loop, daemon=True).start()
log("swipe stimulator started")


try:
    while time.time() - t0 < DURATION + WAIT:
        time.sleep(1)
except KeyboardInterrupt:
    pass
log("done, detaching")
try:
    sess.detach()
except Exception as e:
    log("detach err: " + str(e))
outf.close()

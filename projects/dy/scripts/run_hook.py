# 抖音八神动态抓取 runner: spawn + dy_hook.js, console 落盘
import frida
import sys
import time
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PKG = "com.ss.android.ugc.aweme"
HOOK = sys.argv[2] if len(sys.argv) > 2 else r"D:\reserve_agent\skills-portable-test\projects\dy\hooks\dy_hook.js"
OUT = sys.argv[3] if len(sys.argv) > 3 else r"D:\reserve_agent\skills-portable-test\projects\dy\capture\dy_hook_out.log"
DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 120

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
log(f"spawning {PKG} ...")
pid = dev.spawn([PKG])
log(f"spawned pid={pid}")
session = dev.attach(pid)
script = session.create_script(open(HOOK, encoding="utf-8").read())
script.on("message", on_message)
script.load()
log("script loaded, resuming")
dev.resume(pid)

try:
    while time.time() - t0 < DURATION:
        time.sleep(1)
except KeyboardInterrupt:
    pass
log("done, detaching")
try:
    session.detach()
except Exception as e:
    log("detach err: " + str(e))
outf.close()

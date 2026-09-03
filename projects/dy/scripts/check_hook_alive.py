# 检查 hook 是否被 App 恢复: attach 后 hook 三个点, 间隔 10s 读代码页前 16 字节
# 若首指令 = PACIASP (fa 67 bb a9) → 代码被恢复 (hook 被拆)
# 若首指令 = BR (50 00 1f d6 类跳板) → hook 还在
import frida
import sys
import time
import io
import subprocess
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
PKG = "com.ss.android.ugc.aweme"
ADB = str(Path(__file__).resolve().parents[3] / "android_mcp" / "toolchain" / "bin" / "windows" / "platform-tools" / "adb.exe")

JS = r"""
var base = Module.findBaseAddress("libsscronet.so");
console.log("[base]", base);
var pts = [0x411e74, 0x412680, 0x4127ac];
function snap() {
    var out = [];
    for (var i = 0; i < pts.length; i++) {
        try {
            var b = base.add(pts[i]).readByteArray(16);
            out.push(pts[i].toString(16) + "=" + Array.prototype.map.call(new Uint8Array(b), function (x) { return ("0" + x.toString(16)).slice(-2); }).join(""));
        } catch (e) { out.push(pts[i].toString(16) + "=ERR:" + e); }
    }
    console.log("[snap]", out.join(" "));
}
snap();
setInterval(snap, 10000);
"""

subprocess.run([ADB, "forward", "tcp:27042", "tcp:27042"], check=False)
dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
r = subprocess.run([ADB, "shell", "pidof", PKG], capture_output=True, text=True)
pids = r.stdout.strip().split()
if not pids:
    print("no app pid"); sys.exit(1)
pid = int(pids[0])
print("attach", pid)
sess = dev.attach(pid)
script = sess.create_script(JS)
script.on("message", lambda m, d: print(m.get("payload") if m["type"] != "error" else "JSERR " + str(m.get("description"))[:500]))
script.load()
time.sleep(35)
try:
    sess.detach()
except Exception:
    pass

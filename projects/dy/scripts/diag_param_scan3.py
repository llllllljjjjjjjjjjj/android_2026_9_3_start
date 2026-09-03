# -*- coding: utf-8 -*-
import subprocess
import sys
import time
import frida

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"

JS = r'''
function dumpHits() {
  var out = [];
  var pat = "70 72 6f 70 65 72 74 79 5f 6e 61 6d 65 5f 61 6c 6c";
  var ranges = Process.enumerateRanges("r--");
  ranges.forEach(function (r) {
    if (r.size < 4096 || r.size > 512 * 1024 * 1024) return;
    try {
      var res = Memory.scanSync(r.base, r.size, pat);
      res.forEach(function (m) {
        var hd = "";
        try { hd = hexdump(m.address, { length: 96, ansi: false }); } catch (e) { hd = "ERR " + e.message; }
        out.push({ addr: m.address.toString(), hd: hd });
      });
    } catch (e) {}
  });
  return out;
}
rpc.exports = { d: dumpHits };
send({ t: "ready" });
'''

subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"],
                      stdout=subprocess.DEVNULL)
pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
sess = dev.attach(pid)
sc = sess.create_script(JS)
sc.load()
time.sleep(1)
hits = sc.exports_sync.d()
print("hits:", len(hits))
for h in hits[:3]:
    print("=== addr", h["addr"])
    print(h["hd"])
sess.detach()

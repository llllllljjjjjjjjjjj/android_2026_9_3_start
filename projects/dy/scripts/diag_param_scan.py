# -*- coding: utf-8 -*-
import subprocess
import sys
import time
import frida

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"

JS = r'''
var counts = {};
function scanOne(name, pat) {
  var cnt = 0, sample = "", firstAddr = "";
  var ranges = Process.enumerateRanges("r--");
  ranges.forEach(function (r) {
    if (r.size < 4096 || r.size > 512 * 1024 * 1024) return;
    try {
      var res = Memory.scanSync(r.base, r.size, pat);
      if (res.length > 0) {
        cnt += res.length;
        if (!firstAddr) {
          firstAddr = res[0].address.toString();
          try { sample = res[0].address.readUtf8String(180); } catch (e) {}
        }
      }
    } catch (e) {}
  });
  return { name: name, cnt: cnt, addr: firstAddr, sample: sample };
}
rpc.exports = {
  q: function () { return scanOne("qualification", "71 75 61 6c 69 66 69 63 61 74 69 6f 6e"); },
  p: function () { return scanOne("property_name_all", "70 72 6f 70 65 72 74 79 5f 6e 61 6d 65 5f 61 6c 6c"); },
  v: function () { return scanOne("value", "22 76 61 6c 75 65 22 3a"); },
  n: function () { var r = Process.enumerateRanges("r--"); return r.length; }
};
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
print("pid", pid, "ranges:", sc.exports_sync.n())
for fn in ("q", "p", "v"):
    r = getattr(sc.exports_sync, fn)()
    print(fn, "->", r["name"], "cnt=", r["cnt"], "addr=", r["addr"])
    if r["sample"]:
        print("   sample:", r["sample"][:150])
sess.detach()

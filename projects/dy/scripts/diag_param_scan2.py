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
        // 回溯找最近 '{'
        var start = m.address;
        for (var i = 0; i < 4096; i++) {
          var q = m.address.sub(i);
          try { if (q.readU8() === 0x7b) { start = q; break; } } catch (e) { break; }
        }
        var before = "";
        try { before = m.address.sub(40).readUtf8String(40); } catch (e) {}
        var after = "";
        try { after = m.address.readUtf8String(600); } catch (e) {}
        out.push({ addr: m.address.toString(), before: before, after: after.slice(0, 500) });
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
for h in hits[:4]:
    print("=== addr", h["addr"])
    print("  before:", repr(h["before"]))
    print("  after :", h["after"][:400])
sess.detach()

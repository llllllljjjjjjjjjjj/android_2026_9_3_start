# -*- coding: utf-8 -*-
import subprocess
import sys
import time
import frida

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"

JS = r'''
function scanPat(name, pat, maxhits) {
  var out = [];
  var ranges = Process.enumerateRanges("r--");
  ranges.forEach(function (r) {
    if (r.size < 4096 || r.size > 512 * 1024 * 1024) return;
    var res;
    try { res = Memory.scanSync(r.base, r.size, pat); } catch (e) { return; }
    var n = 0;
    res.forEach(function (m) {
      if (n >= maxhits) return;
      n++;
      var hd = "";
      try { hd = hexdump(m.address, { length: 64, ansi: false }); } catch (e) {}
      out.push({ addr: m.address.toString(), hex: hd });
    });
  });
  return { name: name, count: out.length, hits: out.slice(0, 3) };
}
function pats() {
  return [
    scanPat("property_name_all_utf8", "70 72 6f 70 65 72 74 79 5f 6e 61 6d 65 5f 61 6c 6c", 2),
    scanPat("property_name_all_utf16le", "70 00 72 00 6f 00 70 00 65 00 72 00 74 00 79 00", 2),
    scanPat("prop_esc", "5c 22 70 72 6f 70 65 72 74 79 5f 6e 61 6d 65 5f 61 6c 6c", 2),
    scanPat("cn_shiyong", "e9 80 82 e7 94 a8 e4 ba ba e7 be a4", 2),
    scanPat("cn_putong", "e6 99 ae e9 80 9a e4 ba ba e7 be a4", 2),
    scanPat("cn_ximuyuan", "e6 ba aa e6 9c a8 e6 ba 90", 2),
    scanPat("attr_id", "61 74 74 72 5f 69 64", 2)
  ];
}
rpc.exports = { p: pats };
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
for p in sc.exports_sync.p():
    print(f"== {p['name']} count={p['count']}")
    for h in p["hits"][:2]:
        print("   addr", h["addr"])
        print(h["hex"])
sess.detach()

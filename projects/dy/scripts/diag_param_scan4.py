# -*- coding: utf-8 -*-
import subprocess
import sys
import time
import frida

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"

JS = r'''
function scanQual() {
  var out = [];
  var pat = "71 75 61 6c 69 66 69 63 61 74 69 6f 6e"; // qualification
  var ranges = Process.enumerateRanges("r--");
  ranges.forEach(function (r) {
    if (r.size < 4096 || r.size > 512 * 1024 * 1024) return;
    var res;
    try { res = Memory.scanSync(r.base, r.size, pat); } catch (e) { return; }
    var cnt = 0;
    res.forEach(function (m) {
      if (cnt >= 8) return;
      cnt++;
      try {
        var start = null;
        for (var i = 0; i < 16384; i++) {
          var q = m.address.sub(i);
          try { if (q.readU8() === 0x7b) { start = q; break; } } catch (e) { break; }
        }
        if (!start) return;
        var s = start.readUtf8String(200000);
        // 同时找明文与转义形式
        var hasPlain = s.indexOf('"property_name_all"') >= 0;
        var hasEsc = s.indexOf('\\"property_name_all\\"') >= 0;
        if (!hasPlain && !hasEsc) return;
        var t = s.replace(/\\"/g, '"');
        var g = function (re) { var mm = t.match(re); return mm ? mm[1] : ""; };
        out.push({
          addr: start.toString(),
          plain: hasPlain, esc: hasEsc,
          attr_id: g(/"attr_id":"([^"]*)"/),
          title: g(/"title":"([^"]*)"/),
          names: g(/"property_name_all":"([^"]*)"/),
          values: g(/"value":"([^"]*)"/)
        });
      } catch (e) {}
    });
  });
  return out;
}
rpc.exports = { s: scanQual };
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
hits = sc.exports_sync.s()
print("hits:", len(hits))
for h in hits[:5]:
    print("=== addr", h["addr"], "plain=", h["plain"], "esc=", h["esc"])
    print("  attr_id:", (h["attr_id"] or "")[:80])
    print("  title  :", (h["title"] or "")[:60])
    print("  names  :", (h["names"] or "")[:120])
    print("  values :", (h["values"] or "")[:120])
sess.detach()

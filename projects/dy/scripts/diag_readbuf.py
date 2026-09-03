# -*- coding: utf-8 -*-
import subprocess
import sys
import time
import frida

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"

JS = r'''
var fnGetData = null, fnGetSize = null;
var caps = [];
function hex8(p, n) {
  var s = "";
  for (var i = 0; i < n; i++) { var b = p.add(i).readU8(); s += ("0" + b.toString(16)).slice(-2) + " "; }
  return s.trim();
}
function arm() {
  var c = Process.findModuleByName("libsscronet.so");
  if (!c || fnGetData) return;
  c.enumerateExports().forEach(function (e) {
    if (e.name === "Cronet_Buffer_GetData") fnGetData = new NativeFunction(e.address, 'pointer', ['pointer']);
    if (e.name === "Cronet_Buffer_GetSize") fnGetSize = new NativeFunction(e.address, 'uint64', ['pointer']);
  });
  [0x27765c, 0x1ee748].forEach(function (off) {
    try {
      Interceptor.attach(c.base.add(off), {
        onEnter: function (args) { this.buf = args[2]; },
        onLeave: function () {
          try {
            if (!this.buf || this.buf.isNull() || !fnGetData || !fnGetSize) return;
            var data = fnGetData(this.buf);
            var size = Number(fnGetSize(this.buf));
            if (data.isNull() || size < 4 || size > 2097152) return;
            var h = hex8(data, Math.min(size, 8));
            caps.push({ off: off.toString(16), size: size, head: h, ts: Date.now() });
            if (caps.length > 60) caps.shift();
          } catch (e) {}
        }
      });
    } catch (e) {}
  });
}
arm();
setInterval(arm, 1500);
rpc.exports = {
  list: function () { return caps; },
  reset: function () { caps = []; return "ok"; }
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
sc.exports_sync.reset()
print("open detail ...")
subprocess.check_call([ADB, "shell", "am", "start", "-a",
                       "android.intent.action.VIEW", "-d",
                       "snssdk1128://ec_goods_detail?product_id=3770115268144136255"],
                      stdout=subprocess.DEVNULL)
time.sleep(12)
caps = sc.exports_sync.list()
print("captured buffers:", len(caps))
for c in caps:
    print(f"  off={c['off']} size={c['size']:>8} head={c['head']}")
sess.detach()

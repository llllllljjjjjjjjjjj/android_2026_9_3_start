# search_body_probe4.py — 签名触发后延迟 3 波异步全堆扫描，抓 protobuf body
# 原理：Cronet 的 body 在签名之后才由 UploadDataProvider 提供并写 socket。
# 在 metasec 签名回调(general/stream|single)后 setTimeout 200/800/2000ms 扫描，
# 模式：protobuf string 字段 "?? 07 meishi1"（字段号通配+len7+值）与 "keyword" 明文。
# setTimeout 回调跑在 frida agent 线程，不阻塞目标网络线程。
import frida, sys, time

DEVICE = '127.0.0.1:27042'

JS = r'''
var MS = Process.findModuleByName("libmetasec_ml.so");

function hexdump(ptr, n) {
  var s = "";
  for (var i = 0; i < n; i++) s += ("0" + ptr.add(i).readU8().toString(16)).slice(-2) + (i % 16 === 15 ? "\n" : " ");
  return s;
}

function oneScan(tag) {
  var pats = ["?? 07 6d 65 69 73 68 69 31", "6b 65 79 77 6f 72 64", "1f 8b 08"];
  var ranges = Process.enumerateRanges('r--').filter(function (r) { return r.size > 0x1000; });
  var total = 0;
  pats.forEach(function (pat) {
    var t0 = Date.now();
    ranges.forEach(function (r) {
      var res;
      try { res = Memory.scanSync(r.base, r.size, pat); } catch (e) { return; }
      res.forEach(function (m) {
        total++;
        console.log("[SCAN-" + tag + "] pat=" + pat + " hit=" + m.address);
        try {
          console.log("[SCAN-HEX]\n" + hexdump(m.address.sub(64), 192));
        } catch (e) {}
      });
    });
    console.log("[SCAN-" + tag + "] pat=" + pat + " done in " + (Date.now() - t0) + "ms hits=" + total);
  });
}

Interceptor.attach(MS.base.add(0x28065c), {
  onEnter: function (args) {
    try {
      var u = args[0].isNull() ? "" : args[0].readUtf8String();
      if (!/general\/stream|general\/single/.test(u)) return;
      console.log("[TRIG] " + u.slice(0, 120));
      setTimeout(function () { console.log("[SCAN] wave1 @ 200ms"); oneScan("w1"); }, 200);
      setTimeout(function () { console.log("[SCAN] wave2 @ 800ms"); oneScan("w2"); }, 800);
      setTimeout(function () { console.log("[SCAN] wave3 @ 2000ms"); oneScan("w3"); }, 2000);
    } catch (e) { console.log("[TRIG] err " + e.message); }
  }
});
console.log("[probe4] armed scan-on-sign, metasec=" + MS.base);
'''

def main():
    dev = frida.get_device_manager().add_remote_device(DEVICE)
    target = None
    for p in dev.enumerate_processes():
        if p.name in ('抖音', 'com.ss.android.ugc.aweme'):
            target = p; break
    if not target:
        print('抖音进程未找到'); return
    print('attach pid=%d' % target.pid)
    s = dev.attach(target.pid)
    sc = s.create_script(JS)
    sc.on('message', lambda m, d: print('[msg]', m.get('payload', '') if isinstance(m.get('payload', ''), str) else str(m)[:200]))
    sc.load()
    print('探针已注入，观察 120s（期间请在真机触发一次搜索）……')
    time.sleep(120)

if __name__ == '__main__':
    main()

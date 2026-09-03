// dy_hook34_scan_body.js — 签名触发后延迟 3 波异步全堆扫描，抓 protobuf body
// 原理：Cronet 的 body 在签名之后才由 UploadDataProvider 提供。
// metasec 签名回调(general/stream|single)后 setTimeout 200/800/2000ms 扫描。
// 模式：protobuf string 字段 "?? 07 meishi1" + "keyword" 明文 + gzip 头。
// 用法：frida.exe -H 127.0.0.1:27042 -p <pid> -l dy_hook34_scan_body.js -o /tmp/probe4_out.log

var armed = false;

function hxdump(ptr, n) {
  var s = "";
  for (var i = 0; i < n; i++) s += ("0" + ptr.add(i).readU8().toString(16)).slice(-2) + (i % 16 === 15 ? "\n" : " ");
  return s;
}

function oneScan(tag) {
  var pats = ["?? 07 6d 65 69 73 68 69 31", "6b 65 79 77 6f 72 64", "1f 8b 08"];
  var ranges = Process.enumerateRanges('r--').filter(function (r) { return r.size > 0x1000; });
  console.log("[SCAN-" + tag + "] ranges=" + ranges.length);
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
          console.log("[SCAN-HEX]\n" + hxdump(m.address.sub(64), 256));
        } catch (e) {}
      });
    });
    console.log("[SCAN-" + tag + "] pat=" + pat + " done " + (Date.now() - t0) + "ms total=" + total);
  });
}

function arm() {
  if (armed) return;
  var m = Process.findModuleByName("libmetasec_ml.so");
  if (!m) return;
  try {
    Interceptor.attach(m.base.add(0x28065c), {
      onEnter: function (args) {
        try {
          var u = args[0].isNull() ? "" : args[0].readUtf8String();
          if (!/general\/stream|general\/single/.test(u)) return;
          console.log("[TRIG] " + u.slice(0, 120));
          setTimeout(function () { oneScan("w1"); }, 200);
          setTimeout(function () { oneScan("w2"); }, 800);
          setTimeout(function () { oneScan("w3"); }, 2000);
        } catch (e) { console.log("[TRIG] err " + e.message); }
      }
    });
    armed = true;
    console.log("[hook34] armed scan-on-sign base=" + m.base);
  } catch (e) {
    console.log("[hook34] attach fail: " + e.message);
  }
}

arm();
setInterval(arm, 2000);

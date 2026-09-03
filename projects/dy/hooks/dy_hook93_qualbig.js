// dy_hook93_qualbig.js — 单次大窗口扫描：qualification/资质 上下文 dump 512KB（RPC 手动触发）
var DUMPED = 0;

function scanOnce() {
  if (DUMPED > 0) return DUMPED;
  var pats = [
    "71 75 61 6c 69 66 69 63 61 74 69 6f 6e",  // qualification
    "62 72 61 6e 64 5f 71 75 61 6c",          // brand_qual
    "e8 b5 84 e8 b4 a8"                        // 资质 UTF8
  ];
  var ranges = Process.enumerateRanges("r--");
  var sent = {};
  ranges.forEach(function (r) {
    if (r.size < 4096 || r.size > 512 * 1024 * 1024) return;
    pats.forEach(function (pat) {
      var res;
      try { res = Memory.scanSync(r.base, r.size, pat); } catch (e) { return; }
      res.forEach(function (m) {
        if (DUMPED >= 12) return;
        try {
          var p = m.address, start = null;
          for (var i = 0; i < 16384; i++) {
            var q = p.sub(i);
            try { if (q.readU8() === 0x7b) { start = q; break; } } catch (e) { break; }
          }
          if (!start) return;
          var key = start.toString();
          if (sent[key]) return;
          sent[key] = true;
          var s = start.readUtf8String(524288);
          if (s.indexOf("qualification") < 0 && s.indexOf("资质") < 0 && s.indexOf("brand") < 0) return;
          DUMPED++;
          send({ t: "qual", addr: start.toString(), body: s }, null);
        } catch (e) {}
      });
    });
  });
  send({ t: "done", n: DUMPED });
  return DUMPED;
}

rpc.exports = {
  scan: scanOnce,
  count: function () { return DUMPED; }
};
send({ t: "ready", m: "hook93 loaded" });

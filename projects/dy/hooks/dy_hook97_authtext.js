// dy_hook97_authtext.js — 扫「官方授权/授权书/资质详情」文案上下文，dump 256KB
var DONE = false;
var RESULTS = [];

function scanOnce() {
  if (DONE) return RESULTS;
  var pats = [
    "e5 ae 98 e6 96 b9 e6 8e 88 e6 9d 83",        // 官方授权
    "e6 8e 88 e6 9d 83 e4 b9 a6",                // 授权书
    "e8 b5 84 e8 b4 a8 e8 af a6 e6 83 85",        // 资质详情
    "e6 82 a8 e5 b7 b2 e8 8e b7"                  // 您已获
  ];
  var ranges = Process.enumerateRanges("r--");
  var sent = {};
  ranges.forEach(function (r) {
    if (r.size < 4096 || r.size > 512 * 1024 * 1024) return;
    pats.forEach(function (pat) {
      var res;
      try { res = Memory.scanSync(r.base, r.size, pat); } catch (e) { return; }
      var cnt = 0;
      res.forEach(function (m) {
        if (cnt >= 3) return;
        cnt++;
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
          var s = start.readUtf8String(262144);
          send({ t: "ctx", addr: start.toString(), body: s });
          RESULTS.push(start.toString());
        } catch (e) {}
      });
    });
  });
  DONE = true;
  return RESULTS;
}

rpc.exports = {
  scan: scanOnce,
  count: function () { return RESULTS.length; }
};
send({ t: "ready", m: "hook97 loaded" });

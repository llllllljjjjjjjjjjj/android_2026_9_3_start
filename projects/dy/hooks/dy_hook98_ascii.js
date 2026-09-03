// dy_hook98_ascii.js — ASCII 图片 URL 全量扫描（同 hook94 但只用 ASCII 模式，单次）
var DONE = false;
var RESULTS = [];

function scanOnce() {
  if (DONE) return RESULTS;
  var pats = [
    "64 6f 75 79 69 6e 70 69 63",        // douyinpic
    "70 32 36 2d 73 69 67 6e",          // p26-sign
    "64 65 74 61 69 6c 70 61 67 65",    // detailpage
    "65 63 6f 6d 62 64 69 6d 67",      // ecombdimg
    "62 79 74 65 69 6d 67"             // byteimg
  ];
  var ranges = Process.enumerateRanges("r--");
  var seen = {};
  ranges.forEach(function (r) {
    if (r.size < 4096 || r.size > 512 * 1024 * 1024) return;
    pats.forEach(function (pat) {
      var res;
      try { res = Memory.scanSync(r.base, r.size, pat); } catch (e) { return; }
      res.forEach(function (m) {
        try {
          var p = m.address, start = null;
          for (var i = 0; i < 4096; i++) {
            var q = p.sub(i);
            try { if (q.readU8() === 0x68 && q.readUtf8String(4) === "http") { start = q; break; } } catch (e) {}
          }
          if (!start) return;
          var s = start.readUtf8String(2048);
          var u = s.split(/[\s"\x00\\<>]/)[0];
          if (/^https?:\/\/[^\s]{15,1800}$/.test(u) && /\.(png|jpg|jpeg|webp|heic|gif)/i.test(u)) {
            seen[u] = 1;
          }
        } catch (e) {}
      });
    });
  });
  RESULTS = Object.keys(seen);
  DONE = true;
  return RESULTS;
}

rpc.exports = {
  scan: scanOnce,
  count: function () { return RESULTS.length; }
};
send({ t: "ready", m: "hook98 loaded" });

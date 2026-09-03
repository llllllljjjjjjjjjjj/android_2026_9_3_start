// dy_hook94_picurl.js — 单次扫描 douyinpic/byteimg 图片 URL（无循环，扫完即停）
var DONE = false;
var RESULTS = [];

function scanOnce() {
  if (DONE) return RESULTS;
  var pats = [
    "64 00 6f 00 75 00 79 00 69 00 6e 00 70 00 69 00 63 00",  // douyinpic UTF16
    "74 00 6f 00 73 00 2d 00 63 00 6e 00 2d 00 69 00",        // tos-cn-i UTF16
    "62 00 79 00 74 00 65 00 69 00 6d 00 67 00",              // byteimg UTF16
    "65 00 63 00 6f 00 6d 00 62 00 64 00 69 00 6d 00 67 00"   // ecombdimg UTF16
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
          // 回溯找 "http"（ASCII 或 UTF-16 h\x00t\x00t\x00p\x00）
          var p = m.address, start = null, isUtf16 = false;
          for (var i = 0; i < 4096; i++) {
            var q = p.sub(i);
            try {
              if (q.readU8() === 0x68) {
                if (q.readUtf8String(4) === "http") { start = q; break; }
                if (q.readUtf16String(4) === "http") { start = q; isUtf16 = true; break; }
              }
            } catch (e) {}
          }
          if (!start) return;
          var s = isUtf16 ? start.readUtf16String(2048) : start.readUtf8String(2048);
          var u = s.split(/[\s"\x00\\<>]/)[0];
          if (/^https?:\/\/[^\s]{15,1800}$/.test(u) && /\.(png|jpg|jpeg|webp|heic|gif)/i.test(u)) {
            seen[u] = (seen[u] || 0) + 1;
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
send({ t: "ready", m: "hook94 loaded" });

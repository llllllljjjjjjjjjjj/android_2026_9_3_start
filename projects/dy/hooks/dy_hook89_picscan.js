// dy_hook89_picscan.js — 单次内存扫描图片 URL（RPC picscan()，不循环）
var PICS = [];
var done = false;

function scanOnce() {
  if (done) return PICS;
  var pats = [
    "74 70 6c 76",        // tplv
    "65 63 6f 6d 62 64 69 6d 67", // ecombdimg
    "62 79 74 65 69 6d 67",       // byteimg
    "65 63 6f 6d 2d 73 68 6f 70 2d 6d 61 74 65 72 69 61 6c" // ecom-shop-material
  ];
  var ranges = Process.enumerateRanges("r--");
  var found = {};
  ranges.forEach(function (r) {
    if (r.size < 4096 || r.size > 256 * 1024 * 1024) return;
    pats.forEach(function (pat) {
      var res;
      try { res = Memory.scanSync(r.base, r.size, pat); } catch (e) { return; }
      var cnt = 0;
      res.forEach(function (m) {
        if (cnt >= 8) return;
        cnt++;
        try {
          // 回溯找 "http"
          var p = m.address;
          var start = null;
          for (var i = 0; i < 512; i++) {
            var q = p.sub(i);
            var b = q.readU8();
            if (b === 0x68) { // 'h'
              try {
                if (q.readUtf8String(4) === "http") { start = q; break; }
              } catch (e) {}
            }
          }
          if (!start) return;
          var s = start.readUtf8String(1200);
          var u = s.split(/[\s"\x00\\<>]/)[0];
          if (/^https?:\/\/[^\s]{10,900}$/.test(u) && /\.(png|jpg|jpeg|webp|heic|gif)/i.test(u)) {
            found[u] = (found[u] || 0) + 1;
          }
        } catch (e) {}
      });
    });
  });
  PICS = Object.keys(found);
  done = true;
  return PICS;
}

rpc.exports = {
  picscan: scanOnce,
  count: function () { return PICS.length; }
};
send({ t: "ready", m: "hook89 loaded" });

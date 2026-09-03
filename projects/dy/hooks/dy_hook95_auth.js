// dy_hook95_auth.js — 单次扫描 authorization/brand 上下文，dump 256KB 提取图片 URL
var DONE = false;
var RESULTS = [];

function scanOnce() {
  if (DONE) return RESULTS;
  var pats = [
    "61 75 74 68 6f 72 69 7a 61 74 69 6f 6e",  // authorization
    "62 72 61 6e 64 5f 61 75 74 68",           // brand_auth
    "71 75 61 6c 69 66 69 63 61 74 69 6f 6e",  // qualification
    "e8 b5 84 e8 b4 a8 e8 af a6 e6 83 85"        // 资质详情 UTF8
  ];
  var ranges = Process.enumerateRanges("r--");
  var seen = {};
  var dumped = 0;
  ranges.forEach(function (r) {
    if (r.size < 4096 || r.size > 512 * 1024 * 1024) return;
    pats.forEach(function (pat) {
      var res;
      try { res = Memory.scanSync(r.base, r.size, pat); } catch (e) { return; }
      var cnt = 0;
      res.forEach(function (m) {
        if (cnt >= 5 || dumped >= 10) return;
        cnt++;
        try {
          var p = m.address, start = null;
          for (var i = 0; i < 16384; i++) {
            var q = p.sub(i);
            try { if (q.readU8() === 0x7b) { start = q; break; } } catch (e) { break; }
          }
          if (!start) return;
          var s = start.readUtf8String(262144);
          if (s.indexOf("author") < 0 && s.indexOf("brand") < 0 && s.indexOf("qualif") < 0) return;
          var key = start.toString();
          if (seen[key]) return;
          seen[key] = true;
          dumped++;
          // 提取 http 图片 URL
          var re = /https?:\/\/[^"'\s\\]{10,800}?\.(?:png|jpg|jpeg|webp|heic|gif)[^"'\s\\]*/g;
          var ms = s.match(re) || [];
          ms.forEach(function (u) { if (!seen["u:" + u]) { seen["u:" + u] = true; RESULTS.push(u); } });
          send({ t: "ctx", addr: start.toString(), n: (ms || []).length, head: s.slice(0, 200) });
        } catch (e) {}
      });
    });
  });
  DONE = true;
  send({ t: "done", dumped: dumped, urls: RESULTS.length });
  return RESULTS;
}

rpc.exports = {
  scan: scanOnce,
  count: function () { return RESULTS.length; }
};
send({ t: "ready", m: "hook95 loaded" });

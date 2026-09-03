// dy_hook99_b64.js — 扫 base64 图片数据（JPEG/PNG/WEBP 头），单次 dump 上下文
var DONE = false;
var RESULTS = [];

function scanOnce() {
  if (DONE) return RESULTS;
  var pats = [
    "2f 39 6a 2f",           // /9j/ jpeg b64
    "69 56 42 4f 52 77 30 4b 47 67 6f",  // iVBORw0KGgo png b64
    "55 6b 6c 47 52"         // UklGR webp b64
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
        if (cnt >= 4) return;
        cnt++;
        try {
          var p = m.address, start = null;
          // 回溯找 '"' 或 '{' 字段边界
          for (var i = 0; i < 4096; i++) {
            var q = p.sub(i);
            try {
              var b = q.readU8();
              if (b === 0x22 || b === 0x7b) { start = q; break; }
            } catch (e) { break; }
          }
          if (!start) return;
          var key = start.toString();
          if (sent[key]) return;
          sent[key] = true;
          var s = start.readUtf8String(524288);
          if (s.indexOf("/9j/") < 0 && s.indexOf("iVBOR") < 0 && s.indexOf("UklGR") < 0) return;
          send({ t: "b64", addr: start.toString(), body: s });
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
send({ t: "ready", m: "hook99 loaded" });

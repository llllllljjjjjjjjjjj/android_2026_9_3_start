// dy_hook90_qual.js — 单次扫描 qualification/brand 上下文 JSON，提取 url_list 图片
var RESULT = [];

function scanOnce() {
  if (RESULT.length) return RESULT;
  var pats = [
    "71 75 61 6c 69 66 69 63 61 74 69 6f 6e",  // qualification
    "62 72 61 6e 64 5f 71 75 61 6c",          // brand_qual
    "63 65 72 74 69 66 69 63 61 74 65",       // certificate
    "6c 69 63 65 6e 73 65"                    // license
  ];
  var ranges = Process.enumerateRanges("r--");
  var hits = [];
  ranges.forEach(function (r) {
    if (r.size < 4096 || r.size > 512 * 1024 * 1024) return;
    pats.forEach(function (pat) {
      var res;
      try { res = Memory.scanSync(r.base, r.size, pat); } catch (e) { return; }
      var cnt = 0;
      res.forEach(function (m) {
        if (cnt >= 6) return;
        cnt++;
        try {
          // 回溯找 '{'
          var p = m.address, start = null;
          for (var i = 0; i < 16384; i++) {
            var q = p.sub(i);
            try { if (q.readU8() === 0x7b) { start = q; break; } } catch (e) { break; }
          }
          if (!start) return;
          var s = start.readUtf8String(131072);
          // 提取 url_list 中的图片 URL（最多 30 个）
          var re = /https?:\\?\/\\?\/[^"'\s\\]+?\.(?:png|jpg|jpeg|webp|heic|gif)(?:[^"'\s\\]*)?/gi;
          var ms = s.match(re) || [];
          ms = ms.map(function (u) { return u.replace(/\\\//g, "/"); });
          // 去重并保留顺序
          var uniq = [];
          ms.forEach(function (u) { if (uniq.indexOf(u) < 0 && uniq.length < 40) uniq.push(u); });
          if (uniq.length) {
            hits.push({ addr: start.toString(), n: uniq.length, urls: uniq });
          }
        } catch (e) {}
      });
    });
  });
  // 去重合并
  var all = [];
  hits.forEach(function (h) { h.urls.forEach(function (u) { if (all.indexOf(u) < 0) all.push(u); }); });
  RESULT = { hits: hits.length, urls: all };
  return RESULT;
}

rpc.exports = {
  qual: scanOnce
};
send({ t: "ready", m: "hook90 loaded" });

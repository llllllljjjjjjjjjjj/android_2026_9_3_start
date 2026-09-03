// dy_hook81_mem_aweme.js — 搜索时扫描内存找 aweme_info JSON，dump 完整响应
var found = {};

function scan() {
  // 扫可读内存找 "aweme_info" 字符串
  var ranges = Process.enumerateRanges("r--");
  var hits = 0;
  ranges.forEach(function (r) {
    try {
      if (r.size < 4096 || r.size > 256 * 1024 * 1024) return;
      var res = Memory.scanSync(r.base, r.size, "61 77 65 6d 65 5f 69 6e 66 6f");  // "aweme_info"
      res.forEach(function (m) {
        if (hits >= 10) return;
        // 找到 aweme_info，向前找 JSON 开头（回溯找 {）
        var p = m.address;
        var start = p;
        for (var i = 0; i < 2048; i++) {
          var q = p.sub(i);
          try {
            if (q.readU8() === 0x7b) { start = q; break; }  // '{'
          } catch (e) { break; }
        }
        // 读 JSON 片段
        try {
          var s = start.readUtf8String(2000);
          if (s.indexOf("aweme_id") >= 0 && s.indexOf("desc") >= 0) {
            var key = s.slice(0, 80);
            if (!found[key]) {
              found[key] = true;
              hits++;
              console.log("[AWEME] @ " + start + " len~2000");
              console.log("[AWEME] " + s.slice(0, 800));
            }
          }
        } catch (e) {}
      });
    } catch (e) {}
  });
  console.log("[scan] aweme_info hits=" + hits);
}
setInterval(scan, 2000);
console.log("[hook81] loaded");

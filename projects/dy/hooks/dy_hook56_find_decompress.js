// dy_hook56_find_decompress.js — 枚举 libsscronet 的 zstd/ttzip/decompress 相关导出 + 搜字符串
var sc = null;

function arm() {
  sc = Process.findModuleByName("libsscronet.so");
  if (!sc) return;
  // 1) 导出符号 grep
  var hits = [];
  sc.enumerateExports().forEach(function (e) {
    if (/zstd|ttzip|decompress|dictionary|ZSTD|brotli|br_/i.test(e.name)) hits.push(e.name);
  });
  console.log("[exp] zstd/decompress exports:", hits.length);
  hits.slice(0, 40).forEach(function (n) { console.log("[exp]   " + n); });

  // 2) 搜字符串 ttzip / zstd / template_dict
  var pats = ["ttzip", "zstd", "template_dict", "dictID", "search_api"];
  pats.forEach(function (pat) {
    try {
      var res = Memory.scanSync(sc.base, sc.size, pat);
      console.log("[str] '" + pat + "' hits: " + res.length);
      res.slice(0, 5).forEach(function (m) {
        var off = m.address.sub(sc.base);
        console.log("[str]   " + pat + " @ +0x" + off.toString(16));
      });
    } catch (e) { console.log("[str] " + pat + " scan fail: " + e.message); }
  });
}

arm();
setInterval(arm, 3000);
console.log("[probe] find_decompress loaded");

// dy_hook55_dict_scan2.js — 全内存扫描 zstd 字典，解析 dictID，找 dictID=88 的字典
var found = [];
var scanned = 0;

function hexAt(ptr, n) {
  var out = "";
  for (var i = 0; i < n; i++) out += ("0" + ptr.add(i).readU8().toString(16)).slice(-2);
  return out;
}

var ranges = Process.enumerateRanges("r--");
ranges.forEach(function (r) {
  try {
    var size = Number(r.size);
    if (size < 4096 || size > 512 * 1024 * 1024) return;
    var base = r.base;
    var pages = Math.floor(size / 0x1000);
    for (var i = 0; i < pages; i++) {
      var p = base.add(i * 0x1000);
      try {
        if (p.readU32() === 0xec30a437) {
          // 读 dictID（magic 后 4 字节 LE）
          var dictID = p.add(4).readU32();
          var head = hexAt(p, 16);
          var desc = r.file ? r.file.path : "(anon)";
          console.log("[scan] magic @ " + p + " dictID=" + dictID + " region=" + desc + " head=" + head);
          found.push({ addr: p.toString(), dictID: dictID, head: head });
          if (dictID === 88) {
            console.log("[scan] ★★ 找到 dictID=88 字典 @ " + p + " ★★");
          }
          if (found.length >= 30) return;
        }
      } catch (e) {}
      scanned++;
    }
  } catch (e) {}
  if (found.length >= 30) return;
});
console.log("[scan] done found=" + found.length + " scanned=" + scanned);
send({ t: "done", found: found });

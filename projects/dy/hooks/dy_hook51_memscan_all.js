// dy_hook51_memscan_all.js — 全内存扫描（含匿名区）找 zstd 字典 magic 37a430ec
// 上次 hook50 只扫了有名字的映射；这次扫全部 r-- 区域，发现即上报前 4KB
var found = 0;
var scanned = 0;

function b64from(ptr, n) {
  try {
    var bytes = ptr.readByteArray(n);
    var u8 = new Uint8Array(bytes);
    var bin = "";
    for (var i = 0; i < u8.length; i++) bin += String.fromCharCode(u8[i]);
    return btoa(bin);
  } catch (e) { return null; }
}

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
    // 逐页扫前 4 字节
    var pages = Math.floor(size / 0x1000);
    for (var i = 0; i < pages; i++) {
      var p = base.add(i * 0x1000);
      try {
        if (p.readU32() === 0xec30a437) {
          var head = hexAt(p, 16);
          var desc = r.file ? r.file.path : "(anon)";
          console.log("[hit] @ " + p + " in " + desc + " region=" + size + " head=" + head);
          // 读 4KB 前奏，PC 端再按需读更大
          var b = b64from(p, Math.min(4096, size - i * 0x1000));
          if (b) send({ t: "cand", addr: p.toString(), region: desc, regionSize: size, head: head, b64: b });
          found++;
          if (found >= 20) return;
        }
      } catch (e) {}
      scanned++;
    }
  } catch (e) {}
  if (found >= 20) return;
});
console.log("[scan] done found=" + found + " scanned=" + scanned);

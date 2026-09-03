// dy_hook50_dict_scan.js — 扫描 aweme 进程内存找 zstd 预训练字典
// zstd dict magic = EC 30 A4 37 (LE: 37a430ec)，字典 1KB~512KB
// 找到的候选块 → base64 发回 PC 逐个验证 dictID
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

// 验证候选块：zstd dict 格式 = magic(4) + dictID(4) + entropy tables...
// 只按 magic 找，PC 端用 zstandard 验证
Process.enumerateRanges("r--").forEach(function (r) {
  try {
    // 限制扫描范围：跳过过大匿名区，只扫有名字的 + 堆
    if (r.size > 256 * 1024 * 1024) return;
    if (r.file && !/\.(so|dex|apk|oat|vdex)$/.test(r.file.path)) return;
    var base = r.base;
    var size = Number(r.size);
    if (size < 1024) return;
    var step = 0x1000;
    var chunks = Math.floor(size / step);
    for (var i = 0; i < chunks; i++) {
      var p = base.add(i * step);
      // 快速预检前 4 字节 == 37 a4 30 ec
      try {
        if (p.readU32() === 0xec30a437) {
          // 确认至少 1KB 可读 + 头部合理
          var v = hexAt(p, 16);
          console.log("[scan] candidate @ " + p + " in " + (r.file ? r.file.path : "(anon)") +
                      " head=" + v + " regionSize=" + size);
          var b = b64from(p, Math.min(4096, Number(r.size) - i * step));
          if (b) send({ t: "cand", addr: p.toString(), head: v, b64: b });
        }
      } catch (e) {}
      scanned++;
    }
  } catch (e) {}
});
console.log("[scan] done, scanned=" + scanned);

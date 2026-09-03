// dy_hook60_zstd_xref.js — 定位 ttnet_zstd 字符串 + ADRP xref 找解压函数
var sc = null;
var done = false;

function arm() {
  if (done) return;
  sc = Process.findModuleByName("libsscronet.so");
  if (!sc) return;

  // 1) 搜 zstd 相关字符串的运行时地址
  var pats = ["ttnet_zstd_dict_error", "ttnet_zstd_stream", "TTNET_CONTENT_ZSTD_DECODING_FAILED"];
  pats.forEach(function (pat) {
    try {
      var res = Memory.scanSync(sc.base, sc.size, pat);
      res.forEach(function (m) {
        console.log("[str] '" + pat + "' @ " + m.address + " (off=" + m.address.sub(sc.base) + ")");
        findXrefs(m.address);
      });
    } catch (e) { console.log("[str] " + pat + " scan fail: " + e.message); }
  });
  done = true;
}

function findXrefs(strAddr) {
  // 2) 扫描 .text 段找 ADRP 引用该字符串页
  try {
    var text = null;
    sc.enumerateSections().forEach(function (s) {
      if (s.name === ".text") text = s;
    });
    if (!text) { console.log("[xref] no .text"); return; }
    var page = strAddr.and(ptr(0xfffffffffffff000));
    console.log("[xref] str page = " + page + " scanning .text " + text.address + " size " + text.size);
    var cur = text.address;
    var end = text.address.add(text.size);
    var hits = 0;
    while (cur.compare(end) < 0 && hits < 20) {
      var insn = Instruction.parse(cur);
      if (insn.mnemonic === "adrp") {
        // ADRP: 目标 = (PC & ~0xFFF) + imm*4096
        try {
          var imm = insn.operands[1].value;
          var target = cur.and(ptr(0xfffffffffffff000)).add(imm);
          if (target.equals(page)) {
            var off = cur.sub(sc.base);
            console.log("[xref] ADRP -> '" + hexdump(strAddr, { length: 24 }) + "' @ +0x" + off.toString(16));
            // 找所在函数起点（向前扫）
            var fnStart = cur;
            for (var i = 0; i < 200; i++) {
              var p = cur.sub(i * 4);
              try {
                var ii = Instruction.parse(p);
                if (ii.mnemonic === "stp" || ii.mnemonic === "pacibsp" || ii.mnemonic === "sub") {
                  // 近似函数起点
                  fnStart = p;
                  break;
                }
              } catch (e) { break; }
            }
            console.log("[xref]   函数起点近似 +0x" + fnStart.sub(sc.base).toString(16));
            hits++;
          }
        } catch (e) {}
      }
      cur = cur.add(4);
    }
    console.log("[xref] done, hits=" + hits);
  } catch (e) { console.log("[xref] fail: " + e.message); }
}

arm();
setInterval(arm, 3000);
console.log("[hook60] zstd xref loaded");

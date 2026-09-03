// dy_hook61_zstd_xref2.js — 修正：字符串转 hex pattern 搜 xref
var sc = null;
var done = false;

function strToHex(s) {
  var out = "";
  for (var i = 0; i < s.length; i++) {
    out += ("0" + s.charCodeAt(i).toString(16)).slice(-2) + " ";
  }
  return out.trim();
}

function arm() {
  if (done) return;
  sc = Process.findModuleByName("libsscronet.so");
  if (!sc) return;

  var pats = ["ttnet_zstd_dict_error", "ttnet_zstd_stream", "TTNET_CONTENT_ZSTD_DECODING_FAILED"];
  pats.forEach(function (pat) {
    try {
      var hp = strToHex(pat);
      var res = Memory.scanSync(sc.base, sc.size, hp);
      console.log("[str] '" + pat + "' hits=" + res.length);
      res.forEach(function (m) {
        console.log("[str]   @ " + m.address + " (off=" + m.address.sub(sc.base) + ")");
        findXrefs(m.address);
      });
    } catch (e) { console.log("[str] " + pat + " fail: " + e.message); }
  });
  done = true;
}

function findXrefs(strAddr) {
  try {
    var text = null;
    sc.enumerateSections().forEach(function (s) { if (s.name === ".text") text = s; });
    if (!text) { console.log("[xref] no .text"); return; }
    var page = strAddr.and(ptr(0xfffffffffffff000));
    console.log("[xref] scan .text for ADRP -> page " + page);
    var cur = text.address;
    var end = text.address.add(text.size);
    var hits = 0;
    while (cur.compare(end) < 0 && hits < 20) {
      var insn = Instruction.parse(cur);
      if (insn.mnemonic === "adrp") {
        try {
          var imm = insn.operands[1].value;
          var target = cur.and(ptr(0xfffffffffffff000)).add(imm);
          if (target.equals(page)) {
            var off = cur.sub(sc.base);
            console.log("[xref] ★ ADRP @ +0x" + off.toString(16) + " -> 字符串 " + strAddr);
            // 反汇编前后 8 条，找函数起点
            for (var i = -6; i <= 6; i++) {
              var p = cur.add(i * 4);
              try {
                var ii = Instruction.parse(p);
                var d = ii.toString();
                if (i === 0) console.log("[xref]     " + p.sub(sc.base) + "  >> " + d);
                else console.log("[xref]     " + p.sub(sc.base) + "     " + d);
              } catch (e) {}
            }
            hits++;
          }
        } catch (e) {}
      }
      cur = cur.add(4);
    }
    console.log("[xref] done hits=" + hits);
  } catch (e) { console.log("[xref] fail: " + e.message); }
}

arm();
setInterval(arm, 3000);
console.log("[hook61] loaded");

// dy_hook62_zstd_xref3.js — 只扫 .rodata 段找字符串 + ADRP xref
var sc = null;
var done = false;

function strToHex(s) {
  var out = "";
  for (var i = 0; i < s.length; i++) out += ("0" + s.charCodeAt(i).toString(16)).slice(-2) + " ";
  return out.trim();
}

function arm() {
  if (done) return;
  sc = Process.findModuleByName("libsscronet.so");
  if (!sc) return;

  var rodata = null, text = null;
  sc.enumerateSections().forEach(function (s) {
    if (s.name === ".rodata") rodata = s;
    if (s.name === ".text") text = s;
  });
  if (!rodata) { console.log("[s] no .rodata"); return; }

  var pats = ["ttnet_zstd_dict_error", "ttnet_zstd_stream", "TTNET_CONTENT_ZSTD_DECODING_FAILED",
              "request_ttzip_version", "response_ttzip_version", "zstd_level", "zstd_prefix_path"];
  pats.forEach(function (pat) {
    try {
      var hp = strToHex(pat);
      var res = Memory.scanSync(rodata.address, rodata.size, hp);
      res.forEach(function (m) {
        console.log("[str] '" + pat + "' @ " + m.address + " (off=" + m.address.sub(sc.base) + ")");
        if (text) findXrefs(text, m.address);
      });
    } catch (e) { console.log("[s] " + pat + " fail: " + e.message); }
  });
  done = true;
}

function findXrefs(text, strAddr) {
  var page = strAddr.and(ptr(0xfffffffffffff000));
  var cur = text.address;
  var end = text.address.add(text.size);
  var hits = 0;
  while (cur.compare(end) < 0 && hits < 10) {
    try {
      var insn = Instruction.parse(cur);
      if (insn.mnemonic === "adrp") {
        var imm = insn.operands[1].value;
        var target = cur.and(ptr(0xfffffffffffff000)).add(imm);
        if (target.equals(page)) {
          var off = cur.sub(sc.base);
          console.log("[xref] ★ ADRP @ +0x" + off.toString(16) + " -> 字符串");
          for (var i = -4; i <= 5; i++) {
            try {
              var p = cur.add(i * 4);
              var ii = Instruction.parse(p);
              var tag = (i === 0) ? ">>" : "  ";
              console.log("[xref]     +0x" + p.sub(sc.base).toString(16) + " " + tag + " " + ii.toString());
            } catch (e) {}
          }
          hits++;
        }
      }
    } catch (e) {}
    cur = cur.add(4);
  }
  if (!hits) console.log("[xref] 无 ADRP 引用");
}

arm();
setInterval(arm, 3000);
console.log("[hook62] loaded");

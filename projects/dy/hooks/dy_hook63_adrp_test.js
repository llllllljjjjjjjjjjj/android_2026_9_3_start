// dy_hook63_adrp_test.js — 验证 ADRP operand 语义 + 正确找字符串 xref
var sc = Process.findModuleByName("libsscronet.so");
var text = null, rodata = null;
sc.enumerateSections().forEach(function (s) {
  if (s.name === ".text") text = s;
  if (s.name === ".rodata") rodata = s;
});

// 找 ttnet_zstd_dict_error 字符串地址
function strToHex(s) {
  var out = "";
  for (var i = 0; i < s.length; i++) out += ("0" + s.charCodeAt(i).toString(16)).slice(-2) + " ";
  return out.trim();
}
var res = Memory.scanSync(rodata.address, rodata.size, strToHex("ttnet_zstd_dict_error"));
if (res.length === 0) { console.log("no string"); } else {
  var strAddr = res[0].address;
  var strPage = strAddr.and(ptr(0xfffffffffffff000));
  console.log("string @ " + strAddr + " page " + strPage);

  // 扫 .text 找 ADRP
  var cur = text.address;
  var end = text.address.add(text.size);
  var cnt = 0, hits = 0;
  while (cur.compare(end) < 0 && cnt < 5000000) {
    try {
      var insn = Instruction.parse(cur);
      if (insn.mnemonic === "adrp") {
        var op1 = insn.operands[1];
        // 试两种语义：value 直接是字节偏移，或页偏移
        var v = op1.value;
        // 目标 = PC(页对齐) + v  (v 可能已是 <<12 的字节偏移)
        var target = cur.and(ptr(0xfffffffffffff000)).add(v);
        if (target.equals(strPage)) {
          var off = cur.sub(sc.base);
          console.log("[HIT] ADRP @ +0x" + off.toString(16) + " imm=" + v + " -> 字符串页");
          for (var i = -3; i <= 6; i++) {
            try {
              var p = cur.add(i * 4);
              var ii = Instruction.parse(p);
              var t = (i === 0) ? ">>" : "  ";
              console.log("[HIT]   +0x" + p.sub(sc.base).toString(16) + " " + t + " " + ii.toString());
            } catch (e) {}
          }
          hits++;
          if (hits > 5) break;
        }
      }
    } catch (e) {}
    cur = cur.add(4);
    cnt++;
  }
  console.log("scanned " + cnt + " insns, hits=" + hits);
}

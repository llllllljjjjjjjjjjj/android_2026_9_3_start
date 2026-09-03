// dy_hook64_adrp_dump.js — dump ADRP 指令 operand 语义
var sc = Process.findModuleByName("libsscronet.so");
var text = null;
sc.enumerateSections().forEach(function (s) { if (s.name === ".text") text = s; });

// 找 ttnet_zstd_dict_error 字符串
function strToHex(s) {
  var out = "";
  for (var i = 0; i < s.length; i++) out += ("0" + s.charCodeAt(i).toString(16)).slice(-2) + " ";
  return out.trim();
}
var rodata = null;
sc.enumerateSections().forEach(function (s) { if (s.name === ".rodata") rodata = s; });
var res = Memory.scanSync(rodata.address, rodata.size, strToHex("ttnet_zstd_dict_error"));
var strAddr = res[0].address;
console.log("string @ " + strAddr + " (page " + strAddr.and(ptr(0xfffffffffffff000)) + ")");

// 扫 .text 找 ADRP，dump operand 语义（前 3 个 ADRP）
var cur = text.address;
var end = text.address.add(text.size);
var cnt = 0;
while (cur.compare(end) < 0 && cnt < 3) {
  try {
    var insn = Instruction.parse(cur);
    if (insn.mnemonic === "adrp") {
      var op = insn.operands[1];
      console.log("=== ADRP @ " + cur + " ===");
      console.log("  toString: " + insn.toString());
      console.log("  op type: " + op.type + " value: " + op.value);
      console.log("  operands: " + JSON.stringify(insn.operands.map(function(o){ return {type:o.type, value:o.value}; })));
      // 尝试两种目标计算
      var t1 = cur.and(ptr(0xfffffffffffff000)).add(op.value);
      var t2 = cur.and(ptr(0xfffffffffffff000)).add(op.value * 4096);
      console.log("  目标(直接add value): " + t1 + " vs 字符串页 " + strAddr.and(ptr(0xfffffffffffff000)));
      console.log("  目标(value*4096): " + t2);
      cnt++;
    }
  } catch (e) {}
  cur = cur.add(4);
}

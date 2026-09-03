// dy_hook52c_dump_dict.js — dump 字典候选到设备文件（绕过 send 通道）
var ADDR = ptr("0x79a41c1000");
var OUT = "/data/local/tmp/mem_dict.bin";

function hexAt(ptr, n) {
  var out = "";
  for (var i = 0; i < n; i++) out += ("0" + ptr.add(i).readU8().toString(16)).slice(-2);
  return out;
}

try {
  var sizes = [65536, 262144, 1048576, 4194304];
  var got = 0;
  for (var i = 0; i < sizes.length; i++) {
    try {
      var bytes = ADDR.readByteArray(sizes[i]);
      got = sizes[i];
      var f = new File(OUT, "wb");
      f.write(bytes);
      f.flush();
      f.close();
      console.log("[dump] wrote " + sizes[i] + "B to " + OUT + " head=" + hexAt(ADDR, 16));
      break;
    } catch (e) {
      console.log("[dump] fail " + sizes[i] + ": " + e.message);
    }
  }
  if (!got) console.log("[dump] all failed");
} catch (e) {
  console.log("[dump] err: " + e.message);
}

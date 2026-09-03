// dy_hook52b_dump_dict.js — 直接 dump 字典候选，用 send(data) 二进制通道
var ADDR = ptr("0x79a41c1000");

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
      send({ t: "dump", addr: ADDR.toString(), size: sizes[i], head: hexAt(ADDR, 16) }, bytes);
      console.log("[dump] size=" + sizes[i] + " head=" + hexAt(ADDR, 16));
      break;
    } catch (e) {
      console.log("[dump] fail " + sizes[i] + ": " + e.message);
    }
  }
  if (!got) send({ t: "err", m: "all sizes failed" });
} catch (e) {
  send({ t: "err", m: "dump err: " + e.message });
}

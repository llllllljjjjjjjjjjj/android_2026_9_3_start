// dy_hook52_dump_dict.js — 直接 dump 指定地址的字典候选（读 4MB 上限）
var ADDR = ptr("0x79a41c1000");

function b64from(ptr, n) {
  var bytes = ptr.readByteArray(n);
  var u8 = new Uint8Array(bytes);
  var bin = "";
  for (var i = 0; i < u8.length; i++) bin += String.fromCharCode(u8[i]);
  return btoa(bin);
}

function hexAt(ptr, n) {
  var out = "";
  for (var i = 0; i < n; i++) out += ("0" + ptr.add(i).readU8().toString(16)).slice(-2);
  return out;
}

try {
  // 逐步探测可读长度：先 64KB，再 256KB，再 1MB，再 4MB
  var sizes = [65536, 262144, 1048576, 4194304];
  var got = 0;
  for (var i = 0; i < sizes.length; i++) {
    try {
      var b = b64from(ADDR, sizes[i]);
      got = sizes[i];
      send({ t: "dump", addr: ADDR.toString(), size: sizes[i], head: hexAt(ADDR, 16), b64: b });
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

"use strict";
// native 层抓 HTTP/2 请求头（含签名头）
// 思路：hook libsscronet 的 SSL_write → 拿到 HTTP/2 HEADERS 帧 → 交给 Python 做 HPACK 解码
// 安全：仅 memcpy 一段缓冲并 send（无 Java 对象构造，不碰热路径逻辑）
var target = null;
var pktN = 0;

var LIBGUESS = ["libsscronet.so", "libttboringssl.so"];

function findExport(lib, sym) {
  try {
    var r = new ApiResolver("module");
    var m = r.enumerateMatches("exports:" + lib + "!" + sym);
    if (m && m.length) return m[0].address;
  } catch (e) { }
  return null;
}

function install() {
  // 优先 libsscronet（TTNet 主体），其次 libttboringssl
  var addr = findExport("*libsscronet*", "SSL_write") || findExport("*libttboringssl*", "SSL_write");
  if (!addr) { setTimeout(install, 1200); return; }
  target = addr;
  Interceptor.attach(addr, {
    onEnter: function (args) {
      try {
        var buf = args[1];
        var len = args[2].toInt32();
        if (len <= 4 || len > 262144 || !buf) return;
        pktN++;
        // 只回传可能含 HEADERS 帧的包（帧头 type=0x01）
        var h = new Uint8Array(buf.readByteArray(9));
        var ftype = h[3];
        var isPreface = (h[0] === 0x50 && h[1] === 0x52);
        if (ftype === 1 || isPreface) {
          send({ t: "h", n: pktN, len: len, first: isPreface },
               buf.readByteArray(Math.min(len, 32768)));
        }
      } catch (e) { }
    }
  });
  console.log("[*] hooked SSL_write @ " + addr + " (h2 header capture)");
}
setTimeout(install, 800);

// 占位 rpc，供调用方复位计数
rpc.exports = {
  reset: function () { pktN = 0; return 1; },
  count: function () { return pktN; }
};


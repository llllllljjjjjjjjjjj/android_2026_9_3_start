// dy_hook49_dict_java.js — Java 层抓 zstd 字典 + 搜索响应明文
// 入口1: ZstdDecompressCtx.loadDDict0(byte[]) — 字典原始字节
// 入口2: ZstdDecompressCtx.loadDict(byte[]) — public 包装
// 入口3: ZstdDictDecompress.init(byte[],int,int) — 字典原始字节
// 入口4: ZstdDecompressCtx.decompress(byte[],int) — 解压明文（含搜索响应）
var sent = {};

function b64(bytes) {
  var bin = "";
  for (var i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i] & 0xff);
  return btoa(bin);
}

function hexHead(bytes, n) {
  var out = "";
  for (var i = 0; i < Math.min(n || 24, bytes.length); i++)
    out += ("0" + (bytes[i] & 0xff).toString(16)).slice(-2);
  return out;
}

Java.perform(function () {
  try {
    var Ctx = Java.use("com.bytedance.compression.zstd.ZstdDecompressCtx");
    // loadDDict0(byte[]) 字典字节
    Ctx.loadDDict0.implementation = function (dict) {
      try {
        if (!sent["loadDDict0"]) {
          var arr = Java.array("byte", dict);
          var bytes = [];
          for (var i = 0; i < arr.length; i++) bytes.push(arr[i] & 0xff);
          sent["loadDDict0"] = true;
          send({ t: "dict", tag: "loadDDict0", size: bytes.length, head: hexHead(bytes),
                 b64: b64(bytes) });
          console.log("[dict] loadDDict0 size=" + bytes.length + " head=" + hexHead(bytes));
        }
      } catch (e) { console.log("[dict] loadDDict0 hook err: " + e); }
      return this.loadDDict0(dict);
    };
    // loadDict(byte[]) public 包装（同样抓）
    Ctx.loadDict.overload("[B").implementation = function (dict) {
      try {
        if (!sent["loadDict"]) {
          var bytes = [];
          for (var i = 0; i < dict.length; i++) bytes.push(dict[i] & 0xff);
          sent["loadDict"] = true;
          send({ t: "dict", tag: "loadDict", size: bytes.length, head: hexHead(bytes),
                 b64: b64(bytes) });
          console.log("[dict] loadDict size=" + bytes.length + " head=" + hexHead(bytes));
        }
      } catch (e) {}
      return this.loadDict(dict);
    };
    // decompress(byte[],int) → 明文（可能有搜索响应）
    var dec = Ctx.decompress.overload("[B", "int");
    dec.implementation = function (src, cap) {
      try {
        var out = dec.call(this, src, cap);
        if (out && out.length > 100) {
          var head = "";
          for (var i = 0; i < Math.min(64, out.length); i++) head += String.fromCharCode(out[i]);
          if (head.indexOf("{") >= 0 || /search|aweme|business_data/.test(head)) {
            console.log("[decomp] len=" + out.length + " head=" + head.slice(0, 80));
            send({ t: "plain", tag: "search", size: out.length, head: head.slice(0, 120),
                   b64: b64(out) });
          }
        }
        return out;
      } catch (e) { return dec.call(this, src, cap); }
    };
    console.log("[dict] ZstdDecompressCtx hooked");
  } catch (e) { console.log("[dict] Ctx fail: " + e); }

  try {
    var DD = Java.use("com.bytedance.compression.zstd.ZstdDictDecompress");
    DD.init.implementation = function (dict, off, len) {
      try {
        if (!sent["DDinit"]) {
          var bytes = [];
          for (var i = off; i < off + len && i < dict.length; i++) bytes.push(dict[i] & 0xff);
          sent["DDinit"] = true;
          send({ t: "dict", tag: "DDinit", size: bytes.length, head: hexHead(bytes),
                 b64: b64(bytes) });
          console.log("[dict] DDinit size=" + bytes.length + " head=" + hexHead(bytes));
        }
      } catch (e) {}
      return this.init(dict, off, len);
    };
    console.log("[dict] ZstdDictDecompress hooked");
  } catch (e) { console.log("[dict] DD fail: " + e); }
});
console.log("[dict] hook49 loaded");

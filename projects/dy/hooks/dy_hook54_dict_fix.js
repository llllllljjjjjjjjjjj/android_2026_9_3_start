// dy_hook54_dict_fix.js — 修正偏移 bug，用符号名精确定位 zstd 字典加载函数
var bz = null;
var seen = {};

function hexAt(ptr, n) {
  var out = "";
  for (var i = 0; i < n; i++) out += ("0" + ptr.add(i).readU8().toString(16)).slice(-2);
  return out;
}

function arm() {
  bz = Process.findModuleByName("libbdzstd.so");
  if (!bz) return;
  var done = {};
  function onceByName(name, cb, tag) {
    if (done[name]) return;
    done[name] = true;
    try {
      var a = Module.findExportByName("libbdzstd.so", name);
      if (!a) { console.log("[dict] export not found: " + name); return; }
      Interceptor.attach(a, cb);
      console.log("[dict] armed " + name + " @ " + a);
    } catch (e) { console.log("[dict] " + name + " fail: " + e.message); }
  }
  onceByName("ZSTD_createDDict", {
    onEnter: function (args) {
      var d = args[0]; var n = Number(args[1]);
      if (n > 0 && n < 8 * 1024 * 1024 && !d.isNull()) {
        var key = "createDDict_" + n;
        if (seen[key]) return; seen[key] = true;
        var head = hexAt(d, 16);
        console.log("[dict] createDDict size=" + n + " head=" + head);
        try { send({ t: "dict", tag: key, size: n, head: head }, d.readByteArray(n)); }
        catch (e) { console.log("[dict] read fail: " + e.message); }
      }
    }
  }, "createDDict");
  onceByName("ZSTD_DCtx_loadDictionary", {
    onEnter: function (args) {
      var d = args[1]; var n = Number(args[2]);
      if (n > 0 && n < 8 * 1024 * 1024 && !d.isNull()) {
        var key = "loadDict_" + n;
        if (seen[key]) return; seen[key] = true;
        var head = hexAt(d, 16);
        console.log("[dict] DCtx_loadDictionary size=" + n + " head=" + head);
        try { send({ t: "dict", tag: key, size: n, head: head }, d.readByteArray(n)); }
        catch (e) { console.log("[dict] read fail: " + e.message); }
      }
    }
  }, "DCtx_loadDictionary");
  onceByName("ZSTD_CCtx_loadDictionary", {
    onEnter: function (args) {
      var d = args[1]; var n = Number(args[2]);
      if (n > 0 && n < 8 * 1024 * 1024 && !d.isNull()) {
        var key = "CCtx_loadDict_" + n;
        if (seen[key]) return; seen[key] = true;
        var head = hexAt(d, 16);
        console.log("[dict] CCtx_loadDictionary size=" + n + " head=" + head);
        try { send({ t: "dict", tag: key, size: n, head: head }, d.readByteArray(n)); }
        catch (e) { console.log("[dict] read fail: " + e.message); }
      }
    }
  }, "CCtx_loadDictionary");
  // ZSTD_decompressStream 观测 frame
  onceByName("ZSTD_decompressStream", {
    onEnter: function (args) {
      try {
        var src = args[2].readPointer();
        var sz = args[2].add(8).readU64();
        if (!src.isNull() && sz > 4 && sz < 10 * 1024 * 1024) {
          var b0 = src.readU8(), b1 = src.add(1).readU8(), b2 = src.add(2).readU8(), b3 = src.add(3).readU8();
          if (b0 === 0x28 && b1 === 0xb5 && b2 === 0x2f && b3 === 0xfd) {
            var fhd = src.add(4).readU8();
            var dsz = (fhd >> 1) & 0x3;
            var did = -1;
            if (dsz > 0) { did = 0; for (var i = 0; i < dsz; i++) did |= (src.add(5 + i).readU8() << (8 * i)); }
            console.log("[dict] DECOMPRESS zstd-frame size=" + sz + " dictID=" + did + " ctx=" + args[0]);
          }
        }
      } catch (e) {}
    }
  }, "decompressStream");
}
arm();
setInterval(arm, 2000);
console.log("[dict] fix probe loaded (symbol-based)");

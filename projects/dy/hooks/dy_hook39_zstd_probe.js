// dy_hook39_zstd_probe.js — 定位搜索响应 zstd 解码路径 + 捕获解码后数据
// hook: ZSTD_createDDict（dump 运行时字典）/ ZSTD_decompressStream（dump 输出）/
//       Java ZstdDecompressCtx.decompressByteArray0（JNI 输入输出）
var bz = null;

function hexHead(p, n) {
  var s = "";
  try { for (var i = 0; i < n; i++) s += ("0" + p.add(i).readU8().toString(16)).slice(-2); } catch (e) { s += "??"; }
  return s;
}

function armDDict() {
  var m = Process.findModuleByName("libbdzstd.so");
  if (!m) return;
  try {
    Interceptor.attach(m.base.add(0x6a694), {   // ZSTD_createDDict(dict, size)
      onEnter: function (args) {
        try {
          var size = args[1].toInt32();
          console.log("[DDict] create size=" + size + " head=" + hexHead(args[0], Math.min(64, size)));
        } catch (e) {}
      }
    });
    console.log("[zstd] ZSTD_createDDict armed");
  } catch (e) { console.log("[zstd] DDict fail " + e.message); }
}

function armDecompress() {
  var m = Process.findModuleByName("libbdzstd.so");
  if (!m) return;
  try {
    Interceptor.attach(m.base.add(0x6c8d4), {   // ZSTD_decompressStream(dctx, out, in)
      onEnter: function (args) {
        this.dctx = args[0];
        this.in = args[2];
        try {
          var n = this.in.readU32();            // ZSTD_inBuffer {src, size, pos}
          this.insz = n;
        } catch (e) {}
      },
      onLeave: function (ret) {
        try {
          var r = ret.toInt32();                 // 剩余输入字节（0=完成）
          console.log("[Decomp] ret=" + r + " inSize=" + this.insz);
        } catch (e) {}
      }
    });
    console.log("[zstd] ZSTD_decompressStream armed");
  } catch (e) { console.log("[zstd] Decomp fail " + e.message); }
}

function armJNI() {
  Java.perform(function () {
    try {
      var C = Java.use("com.bytedance.compression.zstd.ZstdDecompressCtx");
      console.log("[zstd] Java class: " + C);
    } catch (e) {
      console.log("[zstd] Java class not found: " + e.message);
      return;
    }
    // 枚举方法，hook 所有返回 byte[] 的 decompress
    var methods = C.class.getDeclaredMethods();
    for (var i = 0; i < methods.length; i++) {
      var mm = methods[i];
      var name = mm.getName();
      if (/decompress/i.test(name)) {
        console.log("[zstd] method: " + name + " " + mm.toGenericString().slice(0, 120));
      }
    }
  });
}

armDDict();
armDecompress();
setInterval(function () {
  armDDict();
  armDecompress();
}, 3000);
setTimeout(armJNI, 3000);
console.log("[zstd] probe loaded");

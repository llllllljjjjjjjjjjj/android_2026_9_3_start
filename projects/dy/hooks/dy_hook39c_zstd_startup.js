// dy_hook39c_zstd_startup.js — spawn 模式：抓启动时字典加载 + 全部 zstd 解压入口
// hook: ZSTD_createDDict / ZSTD_DCtx_loadDictionary / ZSTD_CCtx_loadDictionary /
//       JNI loadDDict/loadFastDictDecompress / ZSTD_decompressStream / JNI decompressByteArray0
var m = null;

function hexHead(p, n) {
  var s = "";
  try { for (var i = 0; i < n; i++) s += ("0" + p.add(i).readU8().toString(16)).slice(-2); } catch (e) { s += "?"; }
  return s;
}

function attach(off, name, argFn, leaveFn) {
  try {
    Interceptor.attach(m.base.add(off), {
      onEnter: function (args) {
        try { if (argFn) argFn(this, args); } catch (e) { console.log("[E] " + name + " enter: " + e.message); }
      },
      onLeave: function (ret) {
        try { if (leaveFn) leaveFn(this, ret); } catch (e) {}
      }
    });
    console.log("[armed] " + name + " @+" + off.toString(16));
  } catch (e) {
    console.log("[fail] " + name + ": " + e.message);
  }
}

function arm() {
  m = Process.findModuleByName("libbdzstd.so");
  if (!m) return false;

  // ZSTD_createDDict(dict, size) → 返回 DDict*
  attach(0x6a694, "ZSTD_createDDict", function (t, a) {
    var size = a[1].toInt32();
    console.log("[DDict] size=" + size + " head=" + hexHead(a[0], Math.min(96, size)));
  });

  // ZSTD_DCtx_loadDictionary(dctx, dict, size)
  attach(0x6c200, "ZSTD_DCtx_loadDictionary", function (t, a) {
    var size = a[2].toInt32();
    console.log("[DLoad] size=" + size + " head=" + hexHead(a[1], Math.min(96, size)));
  });

  // ZSTD_CCtx_loadDictionary(cctx, dict, size)
  attach(0x47024, "ZSTD_CCtx_loadDictionary", function (t, a) {
    var size = a[2].toInt32();
    console.log("[CLoad] size=" + size + " head=" + hexHead(a[1], Math.min(96, size)));
  });

  // ZSTD_decompressStream(dctx, out, in)
  attach(0x6c8d4, "ZSTD_decompressStream", function (t, a) {
    try {
      var n = a[2].readU32();
      console.log("[Decomp] inSize=" + n);
    } catch (e) {}
  }, function (t, r) {
    console.log("[Decomp] ret=" + r.toInt32());
  });

  // JNI ZstdDecompressCtx.loadDDict0
  attach(0x714d0, "JNI_loadDDict0", function (t, a) {
    try {
      var env = Java.vm.getEnv();
      var arr = a[2];
      var len = env.getArrayLength(arr);
      var buf = env.getByteArrayElements(arr, null);
      console.log("[JNI-Dict] len=" + len + " head=" + hexHead(buf, Math.min(96, len)));
      env.releaseByteArrayElements(arr, buf, 0);
    } catch (e) { console.log("[JNI-Dict] err " + e.message); }
  });

  // JNI ZstdDecompressCtx.decompressByteArray0
  attach(0x71634, "JNI_decompressByteArray0", function (t, a) {
    try {
      var env = Java.vm.getEnv();
      var arr = a[2];
      var len = env.getArrayLength(arr);
      console.log("[JNI-Decomp] inLen=" + len);
    } catch (e) {}
  });

  return true;
}

if (!arm()) {
  setInterval(function () { if (arm()) console.log("[zstd] armed"); }, 1000);
} else {
  console.log("[zstd] all armed");
}

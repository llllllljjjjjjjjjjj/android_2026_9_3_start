// dy_hook39b_zstd_java.js — 直接 hook Java zstd 解压入口（含 JNI 层）
// 目标: com.bytedance.compression.zstd.ZstdDecompressCtx.decompressByteArray0
// 及 libbdzstd 的 JNI 导出（按地址 hook，免 Java.perform 时序问题）
var bzArmed = false;

function armNative() {
  var m = Process.findModuleByName("libbdzstd.so");
  if (!m) return;
  // Java_com_bytedance_compression_zstd_ZstdDecompressCtx_decompressByteArray0 @+0x71634
  try {
    Interceptor.attach(m.base.add(0x71634), {
      onEnter: function (args) {
        this.env = args[0];
        try {
          var env = Java.vm.getEnv();
          var inArr = args[2];
          var inLen = args[4].toInt32();
          var buf = env.getByteArrayElements(inArr, null);
          var head = "";
          for (var i = 0; i < Math.min(16, inLen); i++) head += ("0" + buf.add(i).readU8().toString(16)).slice(-2);
          console.log("[JNI] decompressByteArray0 inLen=" + inLen + " head=" + head);
          env.releaseByteArrayElements(inArr, buf, 0);
        } catch (e) {
          console.log("[JNI] enter err: " + e.message);
        }
      },
      onLeave: function (ret) {
        try {
          // 返回值通常为输出长度或状态码
          console.log("[JNI] ret=" + ret.toInt32());
        } catch (e) {}
      }
    });
    console.log("[zstd] native decompressByteArray0 armed @+0x71634");
  } catch (e) {
    console.log("[zstd] native arm fail: " + e.message);
  }
  bzArmed = true;
}

function armJava() {
  Java.perform(function () {
    try {
      var C = Java.use("com.bytedance.compression.zstd.ZstdDecompressCtx");
      var ms = C.class.getDeclaredMethods();
      console.log("[java] class ok, methods:");
      for (var i = 0; i < ms.length; i++) {
        console.log("[java]   " + ms[i].getName() + " " + ms[i].toGenericString().slice(0, 130));
      }
      C.decompressByteArray0.overloads.forEach(function (ov) {
        ov.implementation = function () {
          try {
            var a = arguments;
            var inLen = (a[3] && a[3].toString) ? a[3].toString() : "?";
            console.log("[java] decompressByteArray0 args=" + a.length + " inLen=" + inLen);
          } catch (e) {}
          return ov.apply(this, arguments);
        };
      });
    } catch (e) {
      console.log("[java] fail: " + e.message);
    }
  });
}

armNative();
setInterval(armNative, 3000);
setTimeout(armJava, 2000);
console.log("[zstd] probe39b loaded");

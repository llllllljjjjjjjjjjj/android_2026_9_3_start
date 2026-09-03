// dy_hook77_full.js — hook 28065c onLeave 拿 App 现场生成的签名 + headers，send 完整请求
var MS = null;
function arm() {
  MS = Process.findModuleByName("libmetasec_ml.so");
  if (!MS) return;
  try {
    Interceptor.attach(MS.base.add(0x28065c), {
      onEnter: function (args) {
        try {
          this.url = args[0].isNull() ? "" : args[0].readUtf8String();
          this.headers = args[1].isNull() ? "" : args[1].readUtf8String();
        } catch (e) { this.url = ""; this.headers = ""; }
      },
      onLeave: function (ret) {
        try {
          if (!/general\/(stream|single)/.test(this.url || "")) return;
          var sig = ret.isNull() ? "" : ret.readUtf8String();
          send({ t: "full", url: this.url, headers: this.headers, sig: sig });
        } catch (e) {}
      }
    });
    console.log("[hook77] 28065c onLeave armed");
  } catch (e) {}
}
arm();
setInterval(arm, 1000);
console.log("[hook77] loaded");

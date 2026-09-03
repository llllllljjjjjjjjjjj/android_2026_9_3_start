// dy_hook78_full2.js — 全局变量版：onLeave 拿 App 现场签名 + headers
var MS = null;
var gUrl = "";
var gHeaders = "";
function arm() {
  MS = Process.findModuleByName("libmetasec_ml.so");
  if (!MS) return;
  try {
    Interceptor.attach(MS.base.add(0x28065c), {
      onEnter: function (args) {
        try {
          gUrl = args[0].isNull() ? "" : args[0].readUtf8String();
          gHeaders = args[1].isNull() ? "" : args[1].readUtf8String();
        } catch (e) { gUrl = ""; gHeaders = ""; }
      },
      onLeave: function (ret) {
        try {
          if (!/general\/(stream|single)/.test(gUrl)) return;
          var sig = ret.isNull() ? "" : ret.readUtf8String();
          console.log("[SIG] url=" + gUrl.slice(0, 60));
          console.log("[SIG] sig head=" + sig.slice(0, 50).replace(/\r/g, " "));
          send({ t: "full", url: gUrl, headers: gHeaders, sig: sig });
        } catch (e) { console.log("[SIG] err: " + e.message); }
      }
    });
    console.log("[hook78] armed");
  } catch (e) {}
}
arm();
setInterval(arm, 1000);
console.log("[hook78] loaded");

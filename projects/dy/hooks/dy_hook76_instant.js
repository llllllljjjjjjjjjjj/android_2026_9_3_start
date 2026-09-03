// dy_hook76_instant.js — hook 28065c，onEnter 立即回传 url+headers（毫秒级重放用）
var MS = null;
function arm() {
  MS = Process.findModuleByName("libmetasec_ml.so");
  if (!MS) return;
  try {
    Interceptor.attach(MS.base.add(0x28065c), {
      onEnter: function (args) {
        try {
          var u = args[0].isNull() ? "" : args[0].readUtf8String();
          if (!/general\/(stream|single)/.test(u)) return;
          var h = args[1].isNull() ? "" : args[1].readUtf8String();
          send({ t: "req", url: u, headers: h });
        } catch (e) {}
      }
    });
    console.log("[hook76] 28065c armed");
  } catch (e) {}
}
arm();
setInterval(arm, 1000);
console.log("[hook76] loaded");

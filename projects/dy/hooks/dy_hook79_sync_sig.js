// dy_hook79_sync_sig.js — onEnter 里同步生成签名 + send 完整请求（防递归）
var MS = null;
var f28065c = null;
var inHook = false;

function arm() {
  MS = Process.findModuleByName("libmetasec_ml.so");
  if (!MS) return;
  if (!f28065c) f28065c = new NativeFunction(MS.base.add(0x28065c), 'pointer', ['pointer', 'pointer']);
  try {
    Interceptor.attach(MS.base.add(0x28065c), {
      onEnter: function (args) {
        if (inHook) return;
        var u = "", h = "";
        try {
          u = args[0].isNull() ? "" : args[0].readUtf8String();
          h = args[1].isNull() ? "" : args[1].readUtf8String();
        } catch (e) {}
        if (!/general\/(stream|single)/.test(u)) return;
        inHook = true;
        try {
          // 直接调 28065c 生成签名（App 现场 url+headers）
          var r = f28065c(args[0], args[1]);
          var sig = r.isNull() ? "" : r.readUtf8String();
          send({ t: "full", url: u, headers: h, sig: sig });
        } catch (e) {
          send({ t: "err", m: e.message });
        } finally {
          inHook = false;
        }
      }
    });
    console.log("[hook79] armed");
  } catch (e) { console.log("[hook79] arm fail: " + e.message); }
}
arm();
setInterval(arm, 1000);
console.log("[hook79] loaded");

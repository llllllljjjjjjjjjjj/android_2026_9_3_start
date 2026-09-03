// dy_hook65_dict_url.js — hook 28065c 抓所有含 dict/zstd/config 的请求 url
var MS = null;

function arm() {
  MS = Process.findModuleByName("libmetasec_ml.so");
  if (!MS) return;
  try {
    Interceptor.attach(MS.base.add(0x28065c), {
      onEnter: function (args) {
        try {
          var u = args[0].isNull() ? "" : args[0].readUtf8String();
          if (!u) return;
          if (/dict|zstd|ttzip|config|template/i.test(u)) {
            console.log("[DICT-URL] " + u.slice(0, 160));
          }
        } catch (e) {}
      }
    });
    console.log("[hook65] 28065c armed");
  } catch (e) { console.log("[hook65] arm fail: " + e.message); }
}
arm();
setInterval(arm, 2000);
console.log("[hook65] loaded");

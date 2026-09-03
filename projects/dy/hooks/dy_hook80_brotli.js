// dy_hook80_brotli.js — 枚举 libsscronet 的 brotli 相关导出
var sc = null;
function arm() {
  sc = Process.findModuleByName("libsscronet.so");
  if (!sc) return;
  sc.enumerateExports().forEach(function (e) {
    if (/brotli|Brotli|BR_|decode/i.test(e.name)) console.log("[br] " + e.name + " @ " + e.address);
  });
  // 也搜 libttboringssl / 其他模块
  ["libttboringssl.so", "libttcrypto.so", "libmetasec_ml.so"].forEach(function (mn) {
    var m = Process.findModuleByName(mn);
    if (!m) return;
    m.enumerateExports().forEach(function (e) {
      if (/brotli|Brotli/i.test(e.name)) console.log("[br:" + mn + "] " + e.name + " @ " + e.address);
    });
  });
}
arm();
setInterval(arm, 2000);
console.log("[hook80] loaded");

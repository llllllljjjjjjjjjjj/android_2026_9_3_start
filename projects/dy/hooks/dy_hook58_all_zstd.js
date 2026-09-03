// dy_hook58_all_zstd.js — 枚举 libbdzstd 所有 ZSTD_ 导出，全 hook 看哪个被调
var bz = null;
var armed = {};

function arm() {
  bz = Process.findModuleByName("libbdzstd.so");
  if (!bz) return;
  bz.enumerateExports().forEach(function (e) {
    if (!/^ZSTD_/.test(e.name)) return;
    if (armed[e.name]) return;
    armed[e.name] = true;
    try {
      Interceptor.attach(e.address, {
        onEnter: function (args) {
          // 只打印解压相关（decompress/createD/loadD/refD），忽略压缩
          var n = this._name;
          if (/decompress|DDict|loadD|refD|freeD/i.test(n)) {
            console.log("[ZSTD-CALL] " + n + " args0=" + args[0] + " args1=" + args[1] + " args2=" + args[2]);
            // 尝试读字典指针（loadDDict/createDDict 的 dict 参数）
            try {
              if (/DDict|loadD/i.test(n)) {
                var p = args[1];
                if (p && !p.isNull()) {
                  var head = "";
                  for (var i = 0; i < 16; i++) head += ("0" + p.add(i).readU8().toString(16)).slice(-2);
                  console.log("[ZSTD-DICT] " + n + " dict-head=" + head);
                }
              }
            } catch (e2) {}
          }
        }
      });
    } catch (e) {}
  });
  console.log("[hook58] armed " + Object.keys(armed).length + " ZSTD exports");
}
arm();
setInterval(arm, 2000);
console.log("[hook58] loaded");

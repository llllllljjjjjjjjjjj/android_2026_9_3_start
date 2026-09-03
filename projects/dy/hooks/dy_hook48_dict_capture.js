// dy_hook48_dict_capture.js — 抓 App 用于解压搜索响应的 zstd 预训练字典
// 入口: ZSTD_createDDict(buf, size)  / ZSTD_DCtx_loadDictionary / Java loadDDictFast0
// 策略: 只抓一次（首见字典即保存），输出 base64 + 前 32B hex
var saved = {};
var bz = null;

function whereIs(a) {
  var m = Process.findModuleByAddress(a);
  return m ? m.name + "+0x" + a.sub(m.base).toString(16) : String(a);
}

function trySave(tag, ptr, size) {
  try {
    var n = Number(size);
    if (saved[tag] || n <= 0 || n > 4 * 1024 * 1024 || ptr.isNull()) return;
    saved[tag] = true;
    var bytes = ptr.readByteArray(n);
    var u8 = new Uint8Array(bytes);
    var head = "";
    for (var i = 0; i < Math.min(24, u8.length); i++) head += ("0" + u8[i].toString(16)).slice(-2);
    var bin = "";
    for (var i = 0; i < u8.length; i++) bin += String.fromCharCode(u8[i]);
    send({ t: "dict", tag: tag, size: n, head: head, b64: btoa(bin) });
  } catch (e) {
    send({ t: "err", m: tag + " capture fail: " + e.message });
  }
}

function arm() {
  bz = Process.findModuleByName("libbdzstd.so");
  if (!bz) return;
  var done = {};
  function once(addr, tag, cb) {
    if (done[addr]) return;
    done[addr] = true;
    try {
      Interceptor.attach(addr, cb);
    } catch (e) { console.log("[dict] attach fail " + tag + ": " + e.message); }
  }
  // ZSTD_createDDict(const void* dict, size_t dictSize) → ZSTD_CDict*
  once(bz.base.add(0x56d694), "createDDict", {
    onEnter: function (args) { trySave("createDDict", args[0], args[1]); }
  });
  // ZSTD_DCtx_loadDictionary(ZSTD_DCtx*, const void*, size_t)
  once(bz.base.add(0x56f200), "DCtx_loadDictionary", {
    onEnter: function (args) { trySave("DCtx_loadDictionary", args[1], args[2]); }
  });
  // ZSTD_CCtx_loadDictionary(ZSTD_CCtx*, const void*, size_t)
  once(bz.base.add(0x54a024), "CCtx_loadDictionary", {
    onEnter: function (args) { trySave("CCtx_loadDictionary", args[1], args[2]); }
  });
  console.log("[dict] armed createDDict/loadDictionary");
}

arm();
setInterval(arm, 2500);
console.log("[dict] dict capture probe loaded");

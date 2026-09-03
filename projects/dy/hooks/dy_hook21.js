// dy_hook21.js — 纯 RPC oracle（不挂任何 Interceptor，避免 send 噪音）
// oracle(url, headers) → 八神签名串；oraclebatch([{u,h}...]) → [{i,o,ms}...]
// 28065c = main cb: char*(char*url, char*headers) → "name\r\nvalue\r\n..." 签名串
// ES5 语法（Duktape 兼容），frida 16.5.7 / f1657
var base = null;

function setup() {
  var m = Process.findModuleByName("libmetasec_ml.so");
  if (!m) { return false; }
  base = m.base;
  return true;
}

if (!setup()) { send({ t: "err", m: "metasec not loaded" }); }
else { send({ t: "ready", m: "metasec base=" + base }); }

rpc.exports = {
  oracle: function (url, headers) {
    if (base === null && !setup()) { return "ERR:no-base"; }
    var f = new NativeFunction(base.add(0x28065c), 'pointer', ['pointer', 'pointer']);
    var u = Memory.allocUtf8String(url);
    var h = Memory.allocUtf8String(headers);
    var r = f(u, h);
    try { return r.readUtf8String(); } catch (e) { return "ERR:read:" + e.message; }
  },
  oraclebatch: function (arr) {
    if (base === null && !setup()) { return [{ err: "no-base" }]; }
    var f = new NativeFunction(base.add(0x28065c), 'pointer', ['pointer', 'pointer']);
    var out = [];
    for (var i = 0; i < arr.length; i++) {
      var t0 = Date.now();
      try {
        var u = Memory.allocUtf8String(arr[i].u);
        var h = Memory.allocUtf8String(arr[i].h);
        var r = f(u, h);
        var s;
        if (r.isNull()) { s = "NULL"; }
        else { s = r.readUtf8String(); }
        out.push({ i: i, o: s, ms: Date.now() - t0 });
      } catch (e) {
        out.push({ i: i, o: "ERR:" + e.message, ms: Date.now() - t0 });
      }
    }
    return out;
  },
  getbase: function () {
    if (base === null && !setup()) { return "ERR:no-base"; }
    return base.toString();
  }
};

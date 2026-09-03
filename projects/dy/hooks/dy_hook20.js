// dy_hook20.js — metasec 八神签名核心三层观测 + RPC oracle
// 三层: 28065c(main cb, url/headers → 签名串) / 264E3C(hash core, out/mode/msg) / 274C60(VMP interp)
// RPC:  rpc.exports.oracle(url, headers) → 签名 char*；oracle_batch([{u,h}...]) → [{i,o}...]
// ES5 语法（Duktape 兼容），frida 16.5.7 / f1657
var base = null;

function setup() {
  var m = Process.findModuleByName("libmetasec_ml.so");
  if (!m) { send({ t: "log", m: "metasec not loaded" }); return false; }
  base = m.base;
  send({ t: "log", m: "metasec base=" + base });
  return true;
}

function hexOf(p, n) {
  var out = "";
  try {
    for (var i = 0; i < n; i++) {
      var b = p.add(i).readU8();
      out += ("0" + b.toString(16)).slice(-2);
    }
  } catch (e) { out = "?"; }
  return out;
}

function hookAll() {
  // 1. main cb 28065c: (char*url, char*headers) -> char*
  Interceptor.attach(base.add(0x28065c), {
    onEnter: function (args) {
      this.t0 = Date.now();
      try { this.url = args[0].readUtf8String(); } catch (e) { this.url = "?"; }
      try { this.hdr = args[1].readUtf8String(); } catch (e) { this.hdr = "?"; }
    },
    onLeave: function (ret) {
      var s = "?";
      try { s = ret.readUtf8String(); } catch (e) { }
      send({ t: "cb", ms: Date.now() - this.t0, url: this.url, hdr: this.hdr, out: s });
    }
  });

  // 2. hash core 264E3C(out, mode, msg): dump 入参 + 出参变化
  Interceptor.attach(base.add(0x264E3C), {
    onEnter: function (args) {
      this.out = args[0];
      this.mode = args[1].toInt32();
      var msg = "?";
      try { msg = args[2].readUtf8String(); } catch (e) { }
      send({ t: "hash-in", mode: this.mode, msg: msg, out: hexOf(this.out, 0x40) });
    },
    onLeave: function (ret) {
      send({ t: "hash-out", mode: this.mode, out: hexOf(this.out, 0x40), ret: ret.toString() });
    }
  });

  // 3. VMP interp 274C60(entry, r1..r7)
  Interceptor.attach(base.add(0x274C60), {
    onEnter: function (args) {
      var vals = [];
      for (var i = 0; i < 8; i++) { try { vals.push(args[i].toString()); } catch (e) { vals.push("?"); } }
      send({ t: "vmp", entry: args[0].toString(), vals: vals });
    },
    onLeave: function (ret) {
      send({ t: "vmp-out", ret: ret.toString() });
    }
  });

  // 4. 状态机全局观测: 0x3e5f94/0x3e5fa0/0x3e5fac/0x3e5fa4
  var st = base.add(0x3e5f94);
  send({ t: "state", v: hexOf(st, 0x18) });
}

function boot() {
  if (!setup()) return;
  hookAll();
  send({ t: "ready" });
}

if (base === null) { boot(); }

rpc.exports = {
  oracle: function (url, headers) {
    if (base === null && !setup()) { return "ERR:no-base"; }
    var f = new NativeFunction(base.add(0x28065c), 'pointer', ['pointer', 'pointer']);
    var u = Memory.allocUtf8String(url);
    var h = Memory.allocUtf8String(headers);
    var r = f(u, h);
    return r.readUtf8String();
  },
  oracle_batch: function (arr) {
    if (base === null && !setup()) { return [{ err: "no-base" }]; }
    var f = new NativeFunction(base.add(0x28065c), 'pointer', ['pointer', 'pointer']);
    var out = [];
    for (var i = 0; i < arr.length; i++) {
      try {
        var u = Memory.allocUtf8String(arr[i].u);
        var h = Memory.allocUtf8String(arr[i].h);
        var r = f(u, h);
        out.push({ i: i, o: r.readUtf8String() });
      } catch (e) {
        out.push({ i: i, o: "ERR:" + e.message });
      }
    }
    return out;
  }
};

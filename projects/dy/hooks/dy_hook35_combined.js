// dy_hook35_combined.js — 合并版：证书绕过(FORGE) + 搜索 dump + 延迟 body 扫描
// 单会话解决多会话同址 hook 冲突。
//
// 1) hook30 精简：custom_verify 回调语义反转（API 主机 拒绝1 → 通过0）+ QUIC 降级
// 2) hook33 核心：metasec+0x28065c dump [S] URL + [SH] headers（"name\r\nvalue\r\n..."）
// 3) hook34 核心：签名触发后 setTimeout 200/800/2000ms 异步全堆扫描抓 protobuf body
//
// 用法：frida.exe -H 127.0.0.1:27042 -p <pid> -l dy_hook35_combined.js

var FORGE = true;
var AUTOCLEAR = true;
var certArmed = false;
var dumpArmed = false;
var API_RE = /amemv|qishui|snssdk|bytedance|douyin\.com|iesdouyin|zjcdn|byteimg|bytegoofy/;

var getServername = null;
var getSSLCTX = null;
var errClear = null;
var wrapped = {};

function whereIs(a) {
  var m = Process.findModuleByAddress(a);
  return m ? m.name + "+0x" + a.sub(m.base).toString(16) : String(a);
}

function hostOf(ssl) {
  try {
    if (!getServername || ssl.isNull()) return "(no ssl)";
    var p = getServername(ssl, 0);
    if (p.isNull()) return "(no SNI)";
    return p.readCString();
  } catch (e) { return "(err)"; }
}

function wrapCustomCb(cb, tag) {
  if (cb.isNull() || wrapped[cb.toString()]) return;
  var m = Process.findModuleByAddress(cb);
  if (m && m.name === "libvcn.so") return;
  wrapped[cb.toString()] = true;
  try {
    Interceptor.attach(cb, {
      onEnter: function (args) {
        this.ssl = args[0];
        this.alert = args[1];
        this.host = hostOf(this.ssl);
      },
      onLeave: function (ret) {
        var r = ret.toInt32();
        var h = this.host;
        var isApi = API_RE.test(h);
        if (isApi && r === 1 && FORGE) {
          ret.replace(0);
          try { if (this.alert && !this.alert.isNull()) this.alert.writeU8(0); } catch (e) {}
          console.log("[forge] " + h + " 拒绝(1) → 通过(0)");
        }
        if (isApi && AUTOCLEAR && errClear) {
          try { errClear(); } catch (e) {}
        }
      }
    });
  } catch (e) {
    console.log("[cb] wrap fail " + tag + ": " + e.message);
  }
}

function armCert() {
  if (certArmed) return;
  var b = Process.findModuleByName("libttboringssl.so");
  var c = Process.findModuleByName("libttcrypto.so");
  var s = Process.findModuleByName("libsscronet.so");
  if (!b || !c || !s) return;
  try {
    getServername = new NativeFunction(b.base.add(0x49d6c), 'pointer', ['pointer', 'int']);
    getSSLCTX = new NativeFunction(b.base.add(0x4a638), 'pointer', ['pointer']);
    errClear = new NativeFunction(c.base.add(0xb6014), 'void', []);
  } catch (e) { console.log("[cert] natives init fail: " + e.message); return; }

  // 握手现场：拿 ssl 抓 ctx/cfg 上的 custom_verify 回调
  try {
    Interceptor.attach(b.base.add(0x486c0), {
      onEnter: function (args) {
        this.ssl = args[0];
        try {
          var ctx = getSSLCTX(this.ssl);
          if (!ctx.isNull()) wrapCustomCb(ctx.add(0xC8).readPointer(), "ctx-cb");
          var cfg = this.ssl.add(8).readPointer();
          if (!cfg.isNull()) wrapCustomCb(cfg.add(0x30).readPointer(), "cfg-cb");
        } catch (e) {}
      }
    });
  } catch (e) { console.log("[cert] hs attach fail: " + e.message); }

  // 注册点：直接 wrap 新注册的回调
  try {
    Interceptor.attach(b.base.add(0x49dac), {
      onEnter: function (args) {
        var cb = args[2];
        if (cb.isNull()) return;
        wrapCustomCb(cb, "custom");
      }
    });
    Interceptor.attach(b.base.add(0x49db8), {
      onEnter: function (args) {
        var cb = args[2];
        if (cb.isNull()) return;
        wrapCustomCb(cb, "custom-per-ssl");
      }
    });
  } catch (e) { console.log("[cert] reg attach fail: " + e.message); }

  // QUIC 降级
  try {
    var p = Module.findExportByName("libsscronet.so", "Cronet_EngineParams_enable_quic_set");
    if (p) {
      Interceptor.attach(p, { onEnter: function (args) { args[1] = ptr(0); } });
      console.log("[cert] QUIC 强制关闭 armed");
    }
  } catch (e) {}

  certArmed = true;
  console.log("[cert] FORGE=" + FORGE + " 武装完成");
}

// ---------- 搜索 dump（hook33 核心） ----------
function hxdump(ptr, n) {
  var s = "";
  for (var i = 0; i < n; i++) s += ("0" + ptr.add(i).readU8().toString(16)).slice(-2) + (i % 16 === 15 ? "\n" : " ");
  return s;
}

function oneScan(tag) {
  var pats = ["?? 07 6d 65 69 73 68 69 31", "6b 65 79 77 6f 72 64", "1f 8b 08"];
  var ranges = Process.enumerateRanges('r--').filter(function (r) { return r.size > 0x1000; });
  console.log("[SCAN-" + tag + "] ranges=" + ranges.length);
  var total = 0;
  pats.forEach(function (pat) {
    var t0 = Date.now();
    ranges.forEach(function (r) {
      var res;
      try { res = Memory.scanSync(r.base, r.size, pat); } catch (e) { return; }
      res.forEach(function (m) {
        total++;
        console.log("[SCAN-" + tag + "] pat=" + pat + " hit=" + m.address);
        try {
          console.log("[SCAN-HEX]\n" + hxdump(m.address.sub(64), 256));
        } catch (e) {}
      });
    });
    console.log("[SCAN-" + tag + "] pat=" + pat + " done " + (Date.now() - t0) + "ms total=" + total);
  });
}

function armDump() {
  if (dumpArmed) return;
  var m = Process.findModuleByName("libmetasec_ml.so");
  if (!m) return;
  try {
    Interceptor.attach(m.base.add(0x28065c), {
      onEnter: function (args) {
        try {
          var u = args[0].isNull() ? "" : args[0].readUtf8String();
          if (!/search|suggest|hot_board|billboard/i.test(u)) return;
          console.log("[S] " + u);
          if (/general\/stream|general\/single/.test(u)) {
            setTimeout(function () { oneScan("w1"); }, 200);
            setTimeout(function () { oneScan("w2"); }, 800);
            setTimeout(function () { oneScan("w3"); }, 2000);
          }
          var hp = args[1];
          if (hp.isNull()) {
            console.log("[SH] (null)");
          } else {
            var hex = "";
            for (var i = 0; i < 384; i++) hex += ("0" + hp.add(i).readU8().toString(16)).slice(-2) + (i % 2 === 1 ? " " : "");
            console.log("[SH-HEX] " + hex);
            try {
              var h2 = hp.readUtf8String(16384);
              console.log("[SH] " + (h2 || "(empty)"));
            } catch (e) {
              console.log("[SH] err " + e.message);
            }
          }
        } catch (e) {
          console.log("[S] err " + e.message);
        }
      }
    });
    dumpArmed = true;
    console.log("[dump] armed metasec+0x28065c base=" + m.base);
  } catch (e) {
    console.log("[dump] attach fail: " + e.message);
  }
}

armCert();
armDump();
setInterval(function () { armCert(); armDump(); }, 2000);

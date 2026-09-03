// dy_hook53_refdict.js — hook ZSTD_DCtx_refDDict / ZSTD_createDDict 抓 DDict 对象指针
// 并 hook ZSTD_decompressStream 抓解压输入，找 App 实际用的字典
var bz = null;
var ddictSeen = {};

function whereIs(a) {
  var m = Process.findModuleByAddress(a);
  return m ? m.name + "+0x" + a.sub(m.base).toString(16) : String(a);
}

function scanForMagic(addr, range) {
  // 在 DDict 对象附近扫 37a430ec
  try {
    var base = addr.sub(range / 2);
    for (var off = 0; off < range; off += 4) {
      var p = base.add(off);
      try {
        if (p.readU32() === 0xec30a437) {
          return p.toString();
        }
      } catch (e) { }
    }
  } catch (e) { }
  return null;
}

function arm() {
  bz = Process.findModuleByName("libbdzstd.so");
  if (!bz) return;
  var done = {};
  function once(addr, tag, cb) {
    if (done[addr]) return;
    done[addr] = true;
    try { Interceptor.attach(addr, cb); console.log("[ref] " + tag + " armed @ +" + addr.sub(bz.base).toString(16)); }
    catch (e) { console.log("[ref] " + tag + " fail: " + e.message); }
  }
  // ZSTD_DCtx_refDDict(ZSTD_DCtx*, const ZSTD_DDict*) → 返回 DDict
  once(bz.base.add(0x56f40c), "refDDict", {
    onEnter: function (args) {
      var ddict = args[1];
      if (ddict.isNull()) return;
      var key = ddict.toString();
      if (ddictSeen[key]) return;
      ddictSeen[key] = true;
      // DDict 对象前 0x100 字节 hex
      var head = "";
      for (var i = 0; i < 64; i++) head += ("0" + ddict.add(i).readU8().toString(16)).slice(-2);
      console.log("[ref] DDict=" + ddict + " head=" + head);
      // 附近扫 magic
      var hit = scanForMagic(ddict, 0x4000);
      console.log("[ref] magic near ddict: " + hit);
    }
  });
  // ZSTD_createDDict 重复抓（可能启动后仍有）
  once(bz.base.add(0x56d694), "createDDict", {
    onEnter: function (args) {
      var d = args[0];
      var n = Number(args[1]);
      if (n > 0 && n < 8 * 1024 * 1024) {
        console.log("[ref] createDDict size=" + n + " ptr=" + d + " head=" +
                    d.readU8().toString(16) + d.add(1).readU8().toString(16) + d.add(2).readU8().toString(16) + d.add(3).readU8().toString(16));
      }
    }
  });
  // ZSTD_decompressStream(ZSTD_DCtx*, ZSTD_outBuffer*, ZSTD_inBuffer*) — 抓解压输入 head
  once(bz.base.add(0x56f8d4), "decompressStream", {
    onEnter: function (args) {
      // args[2] = inBuffer* {src, size, pos}
      try {
        var src = args[2].readPointer();
        var sz = args[2].add(8).readU64();
        if (!src.isNull() && sz > 4 && sz < 10 * 1024 * 1024) {
          var b0 = src.readU8().toString(16).padStart(2, "0");
          var b1 = src.add(1).readU8().toString(16).padStart(2, "0");
          var b2 = src.add(2).readU8().toString(16).padStart(2, "0");
          var b3 = src.add(3).readU8().toString(16).padStart(2, "0");
          if (b0 + b1 + b2 + b3 === "28b52ffd") {
            console.log("[ref] DECOMPRESS zstd-frame size=" + sz + " src=" + src + " ctx=" + args[0]);
            // 读 frame header 确定 dictID
            var fhd = src.add(4).readU8();
            var dsz = (fhd >> 1) & 0x3;
            if (dsz === 0) console.log("[ref]   frame no-dictID");
            else {
              var did = 0;
              for (var i = 0; i < dsz; i++) did |= (src.add(5 + i).readU8() << (8 * i));
              console.log("[ref]   frame dictID=" + did + " dsz=" + dsz);
            }
          }
        }
      } catch (e) { }
    }
  });
}

arm();
setInterval(arm, 2000);
console.log("[ref] refdict probe loaded");

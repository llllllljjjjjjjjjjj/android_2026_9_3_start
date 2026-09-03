// dy_hook33_search_dump.js — 搜索接口请求 dump（复用评论接口 hook31 打法）
//
// 1) metasec+0x28065c（八神签名回调）：过滤搜索相关 URL，
//    dump [S] 完整 URL + [SH] 完整 headers 串（"name\r\nvalue\r\n..."，含八神签名头）。
//    评论接口已验证此打法（hook31 只过滤了 comment，故搜索 headers 当时没抓到）。
// 2) libsscronet+0x27765c（Cronet_UploadDataProvider_Read）：
//    onLeave 读 buffer 抓 POST body（onEnter 时 buffer 尚未填充——此前探针的 bug）。
//
// 用法（与 hook30 证书绕过同会话双挂）：
//   .venv-frida-16.5.7/Scripts/frida.exe -H 127.0.0.1:27042 -p <pid> \
//     -l dy_hook30_probe.js -l dy_hook33_search_dump.js -o capture/search_capture3.log
//
// 输出：[S] <url>  [SH] <headers>  [SB] <body>

var base = null;
var armed = false;

function arm() {
  if (armed) return;
  var m = Process.findModuleByName("libmetasec_ml.so");
  if (!m) return;
  base = m.base;
  try {
    Interceptor.attach(base.add(0x28065c), {
      onEnter: function (args) {
        try {
          var u = args[0].isNull() ? "" : args[0].readUtf8String();
          if (!/search|suggest|hot_board|billboard/i.test(u)) return;
          console.log("[S] " + u);
          // 主搜索请求：签名时刻 body 已构建完毕，扫描栈上指针找 gzip/protobuf body
          if (/general\/stream|general\/single/.test(u)) {
            try {
              var bt = Thread.backtrace(this.context, Backtracer.ACCURATE).slice(0, 12).map(function (a) {
                var mod = Process.findModuleByAddress(a);
                return a + (mod ? " " + mod.name + "+0x" + a.sub(mod.base).toString(16) : "");
              });
              console.log("[S-BT] " + bt.join(" | "));
              // 扫描栈 2KB 内所有 8 字节对齐值，解引用找 body 特征
              var sp = this.context.sp;
              var hits = 0;
              for (var off = 0; off < 2048 && hits < 3; off += 8) {
                var pv;
                try { pv = sp.add(off).readPointer(); } catch (e) { continue; }
                if (pv.isNull()) continue;
                var ps = pv.toString(16);
                if (!/^(7[bcde]|0[cde])/.test(ps)) continue; // 堆/so 范围粗滤
                try {
                  var b0 = pv.readU8(), b1 = pv.add(1).readU8();
                  // gzip 头 1f 8b 或 protobuf 首字段特征
                  var isGzip = (b0 === 0x1f && b1 === 0x8b);
                  if (!isGzip && b0 !== 0x0a && b0 !== 0x12) continue;
                  var sizeGuess = isGzip ? 0 : (b0 === 0x0a ? pv.add(1).readU8() : 0);
                  if (!isGzip && (sizeGuess < 2 || sizeGuess > 100)) continue;
                  // 确认含 "meishi"/"keyword" 等文本
                  var probe = "";
                  try { probe = pv.readUtf8String(96); } catch (e) {}
                  var isBody = isGzip || /meishi|keyword|search|general/i.test(probe);
                  if (!isBody) continue;
                  hits++;
                  console.log("[S-BODY-HIT] stackOff=0x" + off.toString(16) + " ptr=" + pv + " gzip=" + isGzip);
                  var hx = "";
                  for (var m = 0; m < 128; m++) hx += ("0" + pv.add(m).readU8().toString(16)).slice(-2) + " ";
                  console.log("[S-BODY-HEX] " + hx);
                } catch (e) {}
              }
              console.log("[S-SCAN] done hits=" + hits);
            } catch (e) {
              console.log("[S-BT] err " + e.message);
            }
          }
          // headers 指针：先 hexdump 384B 看真实格式，再试 utf8
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
    armed = true;
    console.log("[hook33] armed metasec+0x28065c base=" + base);
  } catch (e) {
    console.log("[hook33] attach fail: " + e.message);
  }
}

arm();
setInterval(arm, 2000);

// ---- body 抓取（Cronet 上传路径）----
var readArmed = false;
var fnGetData = null;
var fnGetSize = null;

function armRead() {
  if (readArmed) return;
  var c = Process.findModuleByName("libsscronet.so");
  if (!c) return;
  c.enumerateExports().forEach(function (e) {
    if (e.name === "Cronet_Buffer_GetData") fnGetData = new NativeFunction(e.address, 'pointer', ['pointer']);
    if (e.name === "Cronet_Buffer_GetSize") fnGetSize = new NativeFunction(e.address, 'uint64', ['pointer']);
  });
  try {
    var callNo = 0;
    Interceptor.attach(c.base.add(0x27765c), {
      onEnter: function (args) {
        this.buf = args[2];
        if (callNo < 3) {
          callNo++;
          console.log("[READ] #" + callNo + " self=" + args[0] + " sink=" + args[1] + " buf=" + args[2]);
        }
      },
      onLeave: function (retval) {
        try {
          if (!this.buf || this.buf.isNull() || !fnGetData || !fnGetSize) return;
          // 先验证 buf 指向可读内存：读它前 32 字节
          var probe = this.buf.readU8();
          if (callNo <= 3) {
            var hex0 = "";
            for (var i = 0; i < 32; i++) hex0 += ("0" + this.buf.add(i).readU8().toString(16)).slice(-2) + " ";
            console.log("[READ] buf head: " + hex0);
          }
          var data = fnGetData(this.buf);
          var size = Number(fnGetSize(this.buf));
          if (data.isNull() || size <= 0 || size > 65536) return;
          var txt = data.readUtf8String(Math.min(size, 4096));
          // 只看搜索相关 body（keyword/general/hot 等特征）
          if (!/search|keyword|sug|general|hot|query|billboard/i.test(txt)) return;
          var hex = "";
          var hexLen = Math.min(size, 256);
          for (var i = 0; i < hexLen; i++) {
            hex += ("0" + data.add(i).readU8().toString(16)).slice(-2) + " ";
          }
          console.log("[SB] size=" + size);
          console.log("[SB-TXT] " + txt);
          console.log("[SB-HEX] " + hex);
        } catch (e) {
          console.log("[SB] err " + e.message + " buf=" + this.buf);
        }
      }
    });
    readArmed = true;
    console.log("[hook33] armed Read @ libsscronet+0x27765c getData=" + fnGetData + " getSize=" + fnGetSize);
  } catch (e) {
    console.log("[hook33] Read attach fail: " + e.message);
  }
}

armRead();
setInterval(armRead, 2000);

// ---- body 候选点探针（libsscronet 导出表，0x27765c 是 6 符号共享桩不可用）----
var probeArmed = false;
var probeCount = {};

function armProbe() {
  if (probeArmed) return;
  var c = Process.findModuleByName("libsscronet.so");
  if (!c) return;
  var targets = [
    [0x297ecc, "body_data_set"],
    [0x297efc, "body_data_get"],
    [0x2771e0, "BiStream_SendData"],
    [0x277114, "Buffer_InitWithData"],
    [0x27803c, "http_method_set"],
    [0x277200, "UnsafeWrite"],
    [0x240e84, "RequestStart"]
  ];
  targets.forEach(function (t) {
    try {
      (function (addr, label) {
        Interceptor.attach(c.base.add(addr), {
          onEnter: function (args) {
            this.a0 = args[0];
            this.a1 = args[1];
            this.a2 = args[2];
            this.a3 = args[3];
            probeCount[label] = (probeCount[label] || 0) + 1;
            if (probeCount[label] > 8) return; // 每点只打前 9 次 onEnter 详情
            var line = "[BP-" + label + "] a0=" + args[0] + " a1=" + args[1] + " a2=" + args[2] + " a3=" + args[3];
            try {
              if (!args[0].isNull()) {
                var h0 = "";
                for (var i = 0; i < 16; i++) h0 += ("0" + args[0].add(i).readU8().toString(16)).slice(-2) + " ";
                line += " | a0h:" + h0;
              }
              if (!args[1].isNull()) {
                var h1 = "";
                for (var i = 0; i < 16; i++) h1 += ("0" + args[1].add(i).readU8().toString(16)).slice(-2) + " ";
                line += " | a1h:" + h1;
              }
              if (label === "UnsafeWrite" && !args[1].isNull()) {
                // 疑似 (req, data, len, cb)：dump 数据区 96B 找 gzip/protobuf 特征
                var d = "";
                for (var w = 0; w < 96; w++) d += ("0" + args[1].add(w).readU8().toString(16)).slice(-2) + " ";
                line += "\n  data: " + d;
              }
            } catch (e) {}
            console.log(line);
          },
          onLeave: function (retval) {
            // SendData：解引用 data_obj 内部指针，找 body（gzip 头或 "meishi"）
            if (label !== "BiStream_SendData") return;
            try {
              var p = this.a1;
              if (!p || p.isNull()) return;
              var obj = p.add(8).readPointer();
              if (obj.isNull()) return;
              // obj 内 offset 48-128 的指针全部解引用，内容含 gzip/meishi/general 才打
              var found = 0;
              for (var off = 48; off < 160 && found < 2; off += 8) {
                var dp;
                try { dp = obj.add(off).readPointer(); } catch (e) { continue; }
                if (dp.isNull()) continue;
                var ds = dp.toString(16);
                if (!/^(7[bcde]|0[cde]|12[0-9a-f])/.test(ds)) continue;
                var b0, b1, probe;
                try {
                  b0 = dp.readU8();
                  b1 = dp.add(1).readU8();
                  probe = dp.readUtf8String(64);
                } catch (e) { continue; }
                var isGzip = (b0 === 0x1f && b1 === 0x8b);
                if (!isGzip && !/meishi|general|keyword|search/i.test(probe)) continue;
                found++;
                console.log("[BP-HIT] objOff=0x" + off.toString(16) + " ptr=" + dp + " gzip=" + isGzip);
                var hx = "";
                for (var m = 0; m < 192; m++) hx += ("0" + dp.add(m).readU8().toString(16)).slice(-2) + " ";
                console.log("[BP-HIT-HEX] " + hx);
              }
            } catch (e) {
              console.log("[BP-Leave] err " + e.message);
            }
          }
        });
      })(t[0], t[1]);
    } catch (e) {
      console.log("[BP] fail " + t[1] + ": " + e.message);
    }
  });
  probeArmed = true;
  console.log("[hook33] armed body probes");
}

armProbe();
setInterval(armProbe, 2000);

// ---- provider 捕获：hook upload_data_provider_set 拿 provider vtable，hook 真实 Read ----
var provArmed = false;
var provHooked = 0;

function armProv() {
  if (provArmed) return;
  var c = Process.findModuleByName("libsscronet.so");
  if (!c) return;
  try {
    Interceptor.attach(c.base.add(0x278a10), {
      onEnter: function (args) {
        try {
          var prov = args[1];
          if (prov.isNull()) return;
          var vt = prov.readPointer();
          var mod = Process.findModuleByAddress(vt);
          if (!mod) return;
          console.log("[PROV] provider=" + prov + " vtable=" + vt + " mod=" + mod.name);
          for (var i = 0; i < 4 && provHooked < 4; i++) {
            var fp = vt.add(i * 8).readPointer();
            var fm = Process.findModuleByAddress(fp);
            if (!fm) continue;
            console.log("[PROV] vt[" + i + "]=" + fp + " " + fm.name + "+0x" + fp.sub(fm.base).toString(16));
            if (provHooked >= 1) continue; // 只 hook vt[0]（Read）
            try {
              (function (idx) {
                Interceptor.attach(fp, {
                  onEnter: function (a2) {
                    this.buf = a2[2];
                  },
                  onLeave: function () {
                    try {
                      var b = this.buf;
                      if (!b || b.isNull()) return;
                      var hx = "";
                      for (var m = 0; m < 128; m++) hx += ("0" + b.add(m).readU8().toString(16)).slice(-2) + " ";
                      console.log("[PROV-READ] vt" + idx + " buf: " + hx);
                    } catch (e) {}
                  }
                });
              })(i);
              provHooked++;
              console.log("[PROV] hooked vt[" + i + "]");
            } catch (e) {
              console.log("[PROV] hook vt[" + i + "] fail: " + e.message);
            }
          }
        } catch (e) {
          console.log("[PROV] err " + e.message);
        }
      }
    });
    provArmed = true;
    console.log("[hook33] armed provider probe @ 0x278a10");
  } catch (e) {
    console.log("[hook33] provider attach fail: " + e.message);
  }
}

armProv();
setInterval(armProv, 2000);

// ---- blr x23 @ 0x47aaec：请求构建函数调 metasec 签名的精确指令点 ----
// 此时 x0=URL, x1=headers, x19=请求对象（body 大概率在 x19 对象内）
var blrArmed = false;

function armBlr() {
  if (blrArmed) return;
  var c = Process.findModuleByName("libsscronet.so");
  if (!c) return;
  try {
    Interceptor.attach(c.base.add(0x47aaec), {
      onEnter: function (args) {
        try {
          var x0 = this.context.x0;
          var u = x0.isNull() ? "" : x0.readUtf8String();
          if (!/general\/stream|general\/single/.test(u)) return;
          var x19 = this.context.x19;
          console.log("[BLR] URL=" + u.slice(0, 100));
          console.log("[BLR] x19=" + x19);
          // 扫描 x19 对象 0x1200 字节内指针，解引用找 gzip/meishi
          var found = 0;
          for (var off = 0; off < 0x1200 && found < 2; off += 8) {
            var pv;
            try { pv = x19.add(off).readPointer(); } catch (e) { continue; }
            if (pv.isNull()) continue;
            var ps = pv.toString(16);
            if (!/^(7[bcde]|0[cde]|12)/.test(ps)) continue;
            var b0, b1, probe;
            try {
              b0 = pv.readU8();
              b1 = pv.add(1).readU8();
              probe = pv.readUtf8String(64);
            } catch (e) { continue; }
            var isGzip = (b0 === 0x1f && b1 === 0x8b);
            if (!isGzip && !/meishi|general|keyword|search/i.test(probe)) continue;
            found++;
            console.log("[BLR-HIT] off=0x" + off.toString(16) + " ptr=" + pv + " gzip=" + isGzip);
            var hx = "";
            var hexLen = isGzip ? 1024 : 320;
            for (var m = 0; m < hexLen; m++) hx += ("0" + pv.add(m).readU8().toString(16)).slice(-2) + " ";
            console.log("[BLR-HEX] " + hx);
          }
          console.log("[BLR-SCAN] done found=" + found);
        } catch (e) {
          console.log("[BLR] err " + e.message);
        }
      }
    });
    blrArmed = true;
    console.log("[hook33] armed blr x23 @ 0x47aaec");
  } catch (e) {
    console.log("[hook33] blr attach fail: " + e.message);
  }
}

armBlr();
setInterval(armBlr, 2000);

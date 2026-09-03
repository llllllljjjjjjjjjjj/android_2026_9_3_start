// dy_hook84_feed_play.js — 实时直链采集：feed/详情 URL 打点 + 新鲜 play_addr 提取
//
// 目标：验证"实时 feed 数据内存里含当前有效直链"。
// 1) libmetasec+0x28065c：打印 feed/detail/stream 类 URL（新出现才打）。
// 2) 内存扫描 "play_addr"，要求 URL 含视频 CDN 域名（douyinvod/douyinstatic/byteimg）且带
//    dy_q 参数（直链签名时间戳），只收 dy_q >= 1750000000（2025-06+，排除旧缓存）。
// 3) 还原 \u0026 转义，send 结构化数据 {t:"play", url, ctx}。
//
// 用法: spawn 或 attach 抖音，配合 adb input swipe 触发 feed 刷新。

var MS = null;
var armedSig = false;
var seenUrl = {};

function armSig() {
  if (armedSig) return;
  MS = Process.findModuleByName("libmetasec_ml.so");
  if (!MS) return;
  try {
    Interceptor.attach(MS.base.add(0x28065c), {
      onEnter: function (args) {
        try {
          if (args[0].isNull()) return;
          var u = args[0].readUtf8String();
          if (!u) return;
          if (/feed|detail|stream|play|aweme\/v1|share/i.test(u)) {
            if (!seenUrl[u]) {
              seenUrl[u] = 1;
              console.log("[FURL] " + u.slice(0, 300));
            }
          }
        } catch (e) {}
      }
    });
    armedSig = true;
    console.log("[hook84] sig armed");
  } catch (e) {}
}
armSig();
setInterval(armSig, 2000);

// ---- play_addr 内存扫描（只收新鲜视频直链）----
var sent = {};
var scanBusy = false;

function scan() {
  if (scanBusy) return;
  scanBusy = true;
  try {
    var ranges = Process.enumerateRanges("r--");
    ranges.forEach(function (r) {
      try {
        if (r.size < 4096 || r.size > 256 * 1024 * 1024) return;
        var res = Memory.scanSync(r.base, r.size, "70 6c 61 79 5f 61 64 64 72"); // "play_addr"
        res.forEach(function (m) {
          try {
            var start = m.address;
            for (var i = 0; i < 6144; i++) {
              var q = m.address.sub(i);
              try { if (q.readU8() === 0x7b) { start = q; break; } } catch (e) { break; }
            }
            var s = start.readUtf8String(24000);
            if (s.indexOf("http") < 0) return;
            if (!/douyinvod|douyinstatic|byteimg/.test(s)) return;
            var dyq = s.match(/dy_q=(\d{8,11})/);
            if (!dyq) return;
            var ts = parseInt(dyq[1], 10);
            if (ts < 1750000000) return; // 旧缓存过滤
            // 提取 url_list 中的直链（到引号结束，还原 \u0026）
            var um = s.match(/"(https?:\/\/[^"]+)"/);
            if (!um) return;
            var url = um[1].replace(/\\u0026/g, "&");
            var key = url.slice(0, 120);
            if (sent[key]) return;
            sent[key] = 1;
            send({ t: "play", url: url, ts: ts, ctx: s.slice(0, 4000) });
          } catch (e) {}
        });
      } catch (e) {}
    });
  } finally {
    scanBusy = false;
  }
}
setInterval(scan, 3000);
console.log("[hook84] loaded");

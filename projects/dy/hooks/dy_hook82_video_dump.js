// dy_hook82_video_dump.js — 视频直链探针：URL 端点定位 + play_addr 内存扫描
//
// 1) libmetasec_ml.so+0x28065c（八神签名回调）：全量 dump URL（[VURL]），
//    用于定位视频详情/feed/分享解析接口端点。
// 2) Memory.scanSync 扫 "play_addr" / "url_list" 字符串（native C++ JSON 解析产物），
//    回溯 '{' dump JSON 片段（[VPLAY]），提取直链。
//
// 用法（attach 运行中的抖音主进程）：
//   .venv-frida-16.5.7/Scripts/frida.exe -H 127.0.0.1:27042 -p <pid> \
//     -l dy_hook82_video_dump.js -o capture/video_dump.log
// 或 MCP start_frida_hook 后台会话。

var base = null;
var armed = false;
var seenUrl = {};

function arm() {
  if (armed) return;
  var m = Process.findModuleByName("libmetasec_ml.so");
  if (!m) return;
  base = m.base;
  try {
    Interceptor.attach(base.add(0x28065c), {
      onEnter: function (args) {
        try {
          if (args[0].isNull()) return;
          var u = args[0].readUtf8String();
          if (!u) return;
          seenUrl[u] = (seenUrl[u] || 0) + 1;
          if (seenUrl[u] === 1) {
            console.log("[VURL] " + u);
          } else if (/detail|feed|share|item|video/i.test(u)) {
            console.log("[VURL-x" + seenUrl[u] + "] " + u);
          }
        } catch (e) {}
      }
    });
    armed = true;
    console.log("[hook82] armed metasec+0x28065c base=" + base);
  } catch (e) {
    console.log("[hook82] attach fail: " + e.message);
  }
}

arm();
setInterval(arm, 2000);

// ---- play_addr / url_list 内存扫描（native JSON 解析产物）----
var PATTERNS = [
  { hex: "70 6c 61 79 5f 61 64 64 72", label: "play_addr" },   // play_addr
  { hex: "75 72 6c 5f 6c 69 73 74", label: "url_list" }        // url_list
];
var sent = {};

function scan() {
  var ranges = Process.enumerateRanges("r--");
  ranges.forEach(function (r) {
    try {
      if (r.size < 4096 || r.size > 256 * 1024 * 1024) return;
      PATTERNS.forEach(function (p) {
        var res = Memory.scanSync(r.base, r.size, p.hex);
        res.forEach(function (m) {
          try {
            // 回溯找 JSON 开头 '{'
            var start = m.address;
            for (var i = 0; i < 4096; i++) {
              var q = m.address.sub(i);
              try { if (q.readU8() === 0x7b) { start = q; break; } } catch (e) { break; }
            }
            var s = start.readUtf8String(16000);
            // play_addr 片段必须含直链特征（http + 域名），避免误报
            if (!/http/.test(s)) return;
            if (s.indexOf("aweme_id") < 0 && s.indexOf("play") < 0) return;
            var key = s.slice(0, 80);
            if (sent[key]) return;
            sent[key] = true;
            console.log("[VPLAY-" + p.label + "] " + s);
          } catch (e) {}
        });
      });
    } catch (e) {}
  });
}

setInterval(scan, 2500);
console.log("[hook82] play_addr scanner armed");

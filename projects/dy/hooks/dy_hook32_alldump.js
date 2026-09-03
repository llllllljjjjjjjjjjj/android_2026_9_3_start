// dy_hook32_alldump.js — 全量 dump 28065c 入参 URL（带去重计数）
// hook31 抓不到 comment → 去掉过滤全量抓，人工找评论接口 URL。
// 每 15s 打一次 top 统计；每条新 URL 实时打印。
var base = null;
var armed = false;
var seen = {};   // url -> count

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
          seen[u] = (seen[u] || 0) + 1;
          if (seen[u] === 1) console.log("[NEW] " + u);
        } catch (e) {}
      }
    });
    armed = true;
    console.log("[hook32] armed base=" + base);
  } catch (e) {
    console.log("[hook32] attach fail: " + e.message);
  }
}

arm();
setInterval(arm, 2000);

setInterval(function () {
  var keys = Object.keys(seen);
  keys.sort(function (a, b) { return seen[b] - seen[a]; });
  console.log("[STAT] total " + keys.length + " urls, top:");
  for (var i = 0; i < Math.min(keys.length, 30); i++) {
    console.log("[TOP] x" + seen[keys[i]] + "  " + keys[i]);
  }
}, 15000);

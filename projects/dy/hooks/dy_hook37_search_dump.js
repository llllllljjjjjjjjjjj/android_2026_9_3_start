// dy_hook37_search_dump.js — 搜索接口请求 dump（hook31 评论接口同款打法，零侵入）
//
// 原理：八神签名回调 metasec+0x28065c 的入参 = 每个真实请求的
//   (完整 URL, headers 串 "name\r\nvalue\r\n...")。
// 挂 Interceptor 只读，过滤 URL 含 search 特征 → 搜索接口全貌（含附属接口）。
// 注意：RPC oracle 调用期间不要混入本脚本（oracle 是独立 session）。
//
// 用法：
//   adb forward tcp:27042 tcp:27042
//   python scripts/search_dump.py   （attach 已运行的抖音，日志窗口内触发搜索）
//
// 输出：[S] <url>   [H] <headers>

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
          var u = args[0].isNull() ? "(null)" : args[0].readUtf8String();
          if (!/search|general|sug|suggest/.test(u)) return;   // 只看搜索相关
          var h = args[1].isNull() ? "(null)" : args[1].readUtf8String();
          console.log("[S] " + u);
          console.log("[H] " + h);
        } catch (e) {
          console.log("[S] read err: " + e.message);
        }
      }
    });
    armed = true;
    console.log("[hook37] armed at metasec+0x28065c base=" + base);
  } catch (e) {
    console.log("[hook37] attach fail: " + e.message);
  }
}

arm();
setInterval(arm, 2000);

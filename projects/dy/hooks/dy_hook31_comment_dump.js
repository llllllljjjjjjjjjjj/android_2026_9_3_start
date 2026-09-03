// dy_hook31_comment_dump.js — 评论接口请求 dump（零侵入，只读 28065c 入参）
//
// 原理：八神签名回调 metasec+0x28065c 的入参 = 每个真实请求的
//   (完整 URL, headers 串 "name\r\nvalue\r\n...")。
// 挂 Interceptor 只读，过滤 URL 含 "comment" 的调用 → 评论接口全貌。
// 注意：RPC oracle 调用期间不要混入本脚本（oracle 是独立 session）。
//
// 用法：
//   adb forward tcp:27042 tcp:27042
//   python scripts/comment_dump.py   （attach 已运行的抖音，日志窗口 180s 内刷评论区）
//
// 输出：[C] <url>   [H] <headers>

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
          if (u.indexOf("comment") === -1) return;   // 只看评论相关
          var h = args[1].isNull() ? "(null)" : args[1].readUtf8String();
          console.log("[C] " + u);
          console.log("[H] " + h);
        } catch (e) {
          console.log("[C] read err: " + e.message);
        }
      }
    });
    armed = true;
    console.log("[hook31] armed at metasec+0x28065c base=" + base);
  } catch (e) {
    console.log("[hook31] attach fail: " + e.message);
  }
}

arm();
setInterval(arm, 2000);

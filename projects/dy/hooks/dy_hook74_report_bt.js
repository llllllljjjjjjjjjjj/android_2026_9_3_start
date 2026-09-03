// dy_hook74_report_bt.js — hook 统计上报函数 dump backtrace 定位解压/字典加载
var sc = null;
var TARGETS = [0x49a060, 0x49e054, 0x49dfa0];
var armed = {};

function arm() {
  sc = Process.findModuleByName("libsscronet.so");
  if (!sc) return;
  TARGETS.forEach(function (off) {
    if (armed[off]) return;
    armed[off] = true;
    try {
      Interceptor.attach(sc.base.add(off), {
        onEnter: function (args) {
          var o = this._off;
          var bt = Thread.backtrace(this.context, Backtracer.ACCURATE).slice(0, 30);
          console.log("[RPT +0x" + o.toString(16) + "] ========== 调用栈 ==========");
          for (var i = 0; i < bt.length; i++) {
            var a = bt[i];
            var m = Process.findModuleByAddress(a);
            if (m) console.log("[RPT]   " + m.name + "+0x" + a.sub(m.base).toString(16));
            else console.log("[RPT]   " + a);
          }
        }
      });
    } catch (e) {}
  });
  console.log("[hook74] armed " + Object.keys(armed).length);
}
arm();
setInterval(arm, 2000);
console.log("[hook74] loaded");

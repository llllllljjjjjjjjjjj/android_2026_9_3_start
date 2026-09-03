// dy_hook66_core_trace.js — hook 0x31 区域 zstd 核心函数，触发搜索 dump 参数找字典
var sc = null;
var armed = {};
var TARGETS = [0x319290, 0x3195b8, 0x3196cc, 0x319798, 0x31a004, 0x31a400, 0x319620, 0x31a274, 0x31c51c, 0x31c580];

function ptrInfo(p) {
  // 判断参数是否是指向大 buffer 的指针（可能字典）
  try {
    if (p.isNull()) return "null";
    // 尝试读前 16 字节
    var head = "";
    for (var i = 0; i < 16; i++) head += ("0" + p.add(i).readU8().toString(16)).slice(-2);
    return "ptr[16]=" + head;
  } catch (e) {
    return "ptr?(" + p + ")";
  }
}

function arm() {
  sc = Process.findModuleByName("libsscronet.so");
  if (!sc) return;
  TARGETS.forEach(function (off) {
    if (armed[off]) return;
    armed[off] = true;
    try {
      var addr = sc.base.add(off);
      Interceptor.attach(addr, {
        onEnter: function (args) {
          var o = this._off;
          var bt = Thread.backtrace(this.context, Backtracer.ACCURATE).slice(0, 3);
          var bts = bt.map(function (a) {
            var m = Process.findModuleByAddress(a);
            return m ? m.name + "+0x" + a.sub(m.base).toString(16) : a.toString();
          }).join(" <- ");
          console.log("[core +0x" + o.toString(16) + "] args: " +
                      "x0=" + args[0] + " x1=" + args[1] + " x2=" + args[2] + " x3=" + args[3]);
          console.log("    x0 " + ptrInfo(args[0]));
          console.log("    x1 " + ptrInfo(args[1]));
          console.log("    x2 " + ptrInfo(args[2]));
          console.log("    BT: " + bts);
        }
      });
    } catch (e) {}
  });
  console.log("[hook66] armed " + Object.keys(armed).length + " core funcs");
}
arm();
setInterval(arm, 2000);
console.log("[hook66] loaded");

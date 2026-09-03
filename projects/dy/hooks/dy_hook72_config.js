// dy_hook72_config.js — hook 0x49a720 配置解析，dump config 内容（找字典 url）
var sc = null;

function dumpPtr(p, n) {
  try {
    if (p.isNull()) return "null";
    var s = p.readUtf8String(Math.min(n, 500));
    return s.replace(/[^\x20-\x7e]/g, ".");
  } catch (e) {
    try {
      var head = "";
      for (var i = 0; i < 16; i++) head += ("0" + p.add(i).readU8().toString(16)).slice(-2);
      return "bin:" + head;
    } catch (e2) { return "?"; }
  }
}

function arm() {
  sc = Process.findModuleByName("libsscronet.so");
  if (!sc) return;
  try {
    Interceptor.attach(sc.base.add(0x49a720), {
      onEnter: function (args) {
        var bt = Thread.backtrace(this.context, Backtracer.ACCURATE).slice(0, 4);
        var bts = bt.map(function (a) {
          var m = Process.findModuleByAddress(a);
          return m ? m.name + "+0x" + a.sub(m.base).toString(16) : a.toString();
        }).join(" <- ");
        console.log("[CONFIG] 0x49a720 被调用, BT: " + bts);
        console.log("[CONFIG] X0=" + dumpPtr(args[0], 200));
        console.log("[CONFIG] X1=" + dumpPtr(args[1], 200));
        console.log("[CONFIG] X2=" + dumpPtr(args[2], 1000));
        console.log("[CONFIG] X3=" + dumpPtr(args[3], 1000));
      }
    });
    console.log("[hook72] 0x49a720 armed");
  } catch (e) { console.log("[hook72] arm fail: " + e.message); }
}
arm();
setInterval(arm, 2000);
console.log("[hook72] loaded");

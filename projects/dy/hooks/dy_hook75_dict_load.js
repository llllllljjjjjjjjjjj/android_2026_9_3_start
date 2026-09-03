// dy_hook75_dict_load.js — hook LoadDictMemoryOnFileThread + InitDictOnFileThread，dump 字典路径
var sc = null;
var armed = {};

function readString(p) {
  try {
    if (p.isNull()) return "null";
    // std::string: [0]=ptr, [8]=len (long mode)
    var len = p.add(8).readS64();
    if (len > 0 && len < 4096) {
      return p.readPointer().readUtf8String(len);
    }
    // SSO: [0x17] 是长度
    var ssolen = p.add(0x17).readU8();
    if (ssolen > 0 && ssolen < 23) {
      return p.readUtf8String(ssolen);
    }
    return p.readUtf8String(200);
  } catch (e) { return "err"; }
}

function dumpVector(x1) {
  try {
    var begin = x1.readPointer();
    var end = x1.add(8).readPointer();
    var n = end.sub(begin).toInt32();
    console.log("[DICT] vector begin=" + begin + " end=" + end + " 元素数≈" + (n / 24));
    var cnt = 0;
    var q = begin;
    while (q.compare(end) < 0 && cnt < 20) {
      var s = readString(q);
      console.log("[DICT]   路径: " + s);
      q = q.add(24);  // std::string 是 24 字节
      cnt++;
    }
  } catch (e) { console.log("[DICT] dumpVector err: " + e.message); }
}

function arm() {
  sc = Process.findModuleByName("libsscronet.so");
  if (!sc) return;
  var targets = { 0x49bd04: "LoadDictMemoryOnFileThread", 0x49b40c: "InitDictOnFileThread", 0x49c718: "dictDownload(GET)" };
  Object.keys(targets).forEach(function (off) {
    off = parseInt(off);
    if (armed[off]) return;
    armed[off] = true;
    try {
      Interceptor.attach(sc.base.add(off), {
        onEnter: function (args) {
          var name = this._name;
          console.log("[DICT] === " + name + " 被调用 ===");
          console.log("[DICT]   X0=" + args[0]);
          console.log("[DICT]   X1=" + args[1]);
          if (name === "LoadDictMemoryOnFileThread") {
            dumpVector(args[1]);
          }
          // dump X1 字符串（可能直接是路径）
          console.log("[DICT]   X1 字符串: " + readString(args[1]));
        }
      });
      console.log("[hook75] " + targets[off] + " armed");
    } catch (e) { console.log("[hook75] arm fail: " + e.message); }
  });
}
arm();
setInterval(arm, 2000);
console.log("[hook75] loaded");

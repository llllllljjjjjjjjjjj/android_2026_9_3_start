// dy_hook70_body_probe.js — 无窗口 dump 0x27765c/0x1ee748 的 Read 调用，找 body 上传点
var sc = null;
var fnGetData = null;
var fnGetSize = null;
var armed = {};

function arm() {
  sc = Process.findModuleByName("libsscronet.so");
  if (!sc) return;
  sc.enumerateExports().forEach(function (e) {
    if (e.name === "Cronet_Buffer_GetData") fnGetData = new NativeFunction(e.address, 'pointer', ['pointer']);
    if (e.name === "Cronet_Buffer_GetSize") fnGetSize = new NativeFunction(e.address, 'uint64', ['pointer']);
  });
  [0x27765c, 0x1ee748].forEach(function (off) {
    if (armed[off]) return;
    armed[off] = true;
    try {
      Interceptor.attach(sc.base.add(off), {
        onEnter: function (args) {
          this.off = off;
          this.buf = args[2];
        },
        onLeave: function () {
          try {
            if (!this.buf || this.buf.isNull() || !fnGetData || !fnGetSize) return;
            var data = fnGetData(this.buf);
            var size = Number(fnGetSize(this.buf));
            if (data.isNull() || size < 4 || size > 262144) return;
            var head = "";
            for (var i = 0; i < Math.min(20, size); i++) head += ("0" + data.add(i).readU8().toString(16)).slice(-2);
            // 只打印看起来像 form/zstd 的 body（含 keyword 或 zstd magic）
            if (size > 100 || head.indexOf("282b52") >= 0 || head.indexOf("28b52f") >= 0) {
              console.log("[BODY +0x" + off.toString(16) + "] size=" + size + " head=" + head);
            }
          } catch (e) {}
        }
      });
      console.log("[probe] Read hook +0x" + off.toString(16) + " armed");
    } catch (e) {}
  });
}
arm();
setInterval(arm, 2000);
console.log("[hook70] loaded");

// dy_hook101_alldump.js — hook 28065c + Read provider，全量 buffer dump 到设备文件
var fnGetData = null;
var fnGetSize = null;
var armed = false;
var FH = null;

function openFh() {
  if (FH) return;
  try {
    var File = Java.use("java.io.File");
    var FOS = Java.use("java.io.FileOutputStream");
    FH = FOS.$new("/data/data/com.ss.android.ugc.aweme/files/bufdump.bin", true);
    console.log("[buf] file open");
  } catch (e) {
    console.log("[buf] open fail " + e.message);
  }
}

function arm() {
  if (armed) return;
  var c = Process.findModuleByName("libsscronet.so");
  var m = Process.findModuleByName("libmetasec_ml.so");
  if (!c || !m) return;
  c.enumerateExports().forEach(function (e) {
    if (e.name === "Cronet_Buffer_GetData") fnGetData = new NativeFunction(e.address, 'pointer', ['pointer']);
    if (e.name === "Cronet_Buffer_GetSize") fnGetSize = new NativeFunction(e.address, 'uint64', ['pointer']);
  });
  // 请求 URL（用于标记）
  Interceptor.attach(m.base.add(0x28065c), {
    onEnter: function (args) {
      try {
        var u = args[0].isNull() ? "" : args[0].readUtf8String();
        if (/ecombdapi|amemv|douyin/.test(u) && FH) {
          var tag = "[URL]" + u + "\n";
          var Bytes = Java.use("[B");
          var jstr = Java.use("java.lang.String").$new(tag);
          FH.write(jstr.getBytes("UTF-8"));
          FH.flush();
        }
      } catch (e) {}
    }
  });
  // Read buffer（上下行都会过）
  [0x27765c, 0x1ee748].forEach(function (off) {
    try {
      Interceptor.attach(c.base.add(off), {
        onEnter: function (args) { this.buf = args[2]; },
        onLeave: function () {
          try {
            if (!this.buf || this.buf.isNull() || !fnGetData || !fnGetSize || !FH) return;
            var data = fnGetData(this.buf);
            var size = Number(fnGetSize(this.buf));
            if (data.isNull() || size < 4 || size > 2097152) return;
            var bytes = data.readByteArray(size);
            if (bytes === null) return;
            // 只存文本类（JSON/form/plain）或 zstd/ttzip 头
            var head = "";
            try { head = data.readUtf8String(Math.min(size, 64)); } catch (e) {}
            if (!/[a-zA-Z{[]/.test(head)) return;
            var hdr = Java.use("java.lang.String").$new("[BUF]" + size + "@" + off.toString(16) + "\n");
            FH.write(hdr.getBytes("UTF-8"));
            FH.write(bytes);
            var nl = Java.use("java.lang.String").$new("\n[END]\n");
            FH.write(nl.getBytes("UTF-8"));
            FH.flush();
          } catch (e) {}
        }
      });
    } catch (e) {}
  });
  armed = true;
  console.log("[buf] armed");
}

Java.perform(openFh);
setInterval(function () { Java.perform(openFh); arm(); }, 1500);
arm();
rpc.exports = {
  size: function () {
    try {
      var File = Java.use("java.io.File");
      var f = File.$new("/data/data/com.ss.android.ugc.aweme/files/bufdump.bin");
      return f.exists() ? f.length() : -1;
    } catch (e) { return -2; }
  }
};
send({ t: "ready", m: "hook101 loaded" });

// dy_hook68_sslread.js — hook SSL_read 抓解密后响应，检测 br vs zstd magic
var bssl = null;

function arm() {
  bssl = Process.findModuleByName("libttboringssl.so");
  if (!bssl) return;
  var ssl_read = bssl.findExportByName("SSL_read");
  if (!ssl_read) {
    // 备选：枚举导出找 read
    bssl.enumerateExports().forEach(function (e) {
      if (/SSL_read|ssl_read/i.test(e.name)) ssl_read = e.address;
    });
  }
  if (!ssl_read) { console.log("[ssl] SSL_read not found"); return; }
  try {
    Interceptor.attach(ssl_read, {
      onEnter: function (args) {
        this.buf = args[1];
        this.len = args[2].toInt32();
      },
      onLeave: function (ret) {
        var n = ret.toInt32();
        if (n <= 0 || n > 1024 * 1024) return;
        try {
          var b0 = this.buf.readU8(), b1 = this.buf.add(1).readU8();
          var b2 = this.buf.add(2).readU8(), b3 = this.buf.add(3).readU8();
          // br magic 通常是 0xXX (brotli 无固定 magic)，zstd = 28 b5 2f fd
          if (b0 === 0x28 && b1 === 0xb5 && b2 === 0x2f && b3 === 0xfd) {
            console.log("[SSL-READ] ★ zstd frame magic, len=" + n);
            // dump 前 16 字节
            var head = "";
            for (var i = 0; i < 16; i++) head += ("0" + this.buf.add(i).readU8().toString(16)).slice(-2);
            console.log("[SSL-READ]   head=" + head);
          } else if (n > 4) {
            // 检查是否 HTTP 响应头（含 content-encoding）
            var s = "";
            try { s = this.buf.readUtf8String(Math.min(n, 512)); } catch (e) {}
            if (/content-encoding|HTTP\/|200 OK/.test(s)) {
              var ce = (s.match(/content-encoding:\s*([^\r\n]+)/i) || [])[1] || "?";
              console.log("[SSL-READ] HTTP 响应, content-encoding=" + ce + " len=" + n);
            }
          }
        } catch (e) {}
      }
    });
    console.log("[ssl] SSL_read armed @ " + ssl_read);
  } catch (e) { console.log("[ssl] arm fail: " + e.message); }
}
arm();
setInterval(arm, 3000);
console.log("[hook68] loaded");

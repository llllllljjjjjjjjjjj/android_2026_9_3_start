// dy_hook69_ce.js — dump App 搜索响应的 content-encoding 头
var bssl = null;
function arm() {
  bssl = Process.findModuleByName("libttboringssl.so");
  if (!bssl) return;
  var ssl_read = bssl.findExportByName("SSL_read");
  if (!ssl_read) return;
  try {
    Interceptor.attach(ssl_read, {
      onEnter: function (args) { this.buf = args[1]; this.len = args[2].toInt32(); },
      onLeave: function (ret) {
        var n = ret.toInt32();
        if (n <= 0 || n > 1024 * 1024) return;
        try {
          var s = this.buf.readUtf8String(Math.min(n, 2000));
          // 找 content-encoding
          var m = s.match(/content-encoding:\s*([^\r\n]+)/i);
          var path = s.match(/(GET|POST)\s+([^\s]+)/);
          if (m || (path && /search|aweme/.test(path[2]))) {
            console.log("[CE] " + (m ? m[1] : "?") + " | " + (path ? path[2].slice(0, 80) : "?"));
          }
        } catch (e) {}
      }
    });
    console.log("[hook69] SSL_read armed");
  } catch (e) {}
}
arm();
setInterval(arm, 3000);

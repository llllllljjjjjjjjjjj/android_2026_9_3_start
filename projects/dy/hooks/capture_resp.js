"use strict";
// 抓 libttboringssl 的 SSL_read（响应明文），二进制回传 Python 落盘
var libname = "*libttboringssl*";
var SSL_read_addr = null;

function resolve() {
  var resolver = new ApiResolver("module");
  var m = resolver.enumerateMatches("exports:" + libname + "!SSL_read");
  if (!m || m.length === 0) return false;
  SSL_read_addr = m[0].address;
  return true;
}

function install() {
  if (!resolve()) { setTimeout(install, 1000); return; }
  Interceptor.attach(SSL_read_addr, {
    onEnter: function (args) { this.buf = args[1]; },
    onLeave: function (retval) {
      retval |= 0;
      if (retval <= 0) return;
      try { send({ t: "read" }, this.buf.readByteArray(retval)); } catch (e) { }
    }
  });
  console.log("[*] hooked SSL_read on libttboringssl");
}
setTimeout(install, 800);

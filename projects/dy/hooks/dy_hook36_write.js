// dy_hook36_write.js — hook libc write/sendto/sendmsg/writev，抓搜索请求的完整 HTTP 报文
// 与 hook35 无同址冲突（不同地址），可并行挂载。
// 过滤：buffer 头部含 POST/GET/general/search/meishi 才 dump。
// 目标：POST /aweme/v2/search/general/stream 的 body（gzip 或明文）。

var armed = false;

function dumpBuf(ptr, n, tag) {
  console.log("[" + tag + "] size=" + n);
  var hex = "";
  var hn = Math.min(n, 2048);
  for (var i = 0; i < hn; i++) hex += ("0" + ptr.add(i).readU8().toString(16)).slice(-2) + (i % 16 === 15 ? "\n" : " ");
  console.log("[" + tag + "-HEX]\n" + hex);
  try {
    console.log("[" + tag + "-TXT]\n" + ptr.readUtf8String(Math.min(n, 4096)));
  } catch (e) {}
}

function check(ptr, n, tag) {
  try {
    if (n < 40 || n > 262144) return;
    var head = ptr.readUtf8String(Math.min(n, 80));
    if (!/POST|GET|general|meishi|search|aweme/i.test(head)) return;
    dumpBuf(ptr, n, tag);
  } catch (e) {}
}

function arm() {
  if (armed) return;
  var lc = Process.findModuleByName("libc.so");
  if (!lc) return;
  try {
    var w = Module.findExportByName("libc.so", "write");
    Interceptor.attach(w, {
      onEnter: function (a) { this.b = a[1]; this.n = a[2].toInt32(); },
      onLeave: function () { check(this.b, this.n, "W-write"); }
    });
    console.log("[hook36] write @ " + w);
  } catch (e) { console.log("[hook36] write fail " + e.message); }
  try {
    var st = Module.findExportByName("libc.so", "sendto");
    Interceptor.attach(st, {
      onEnter: function (a) { this.b = a[1]; this.n = a[2].toInt32(); },
      onLeave: function () { check(this.b, this.n, "W-sendto"); }
    });
    console.log("[hook36] sendto @ " + st);
  } catch (e) { console.log("[hook36] sendto fail " + e.message); }
  try {
    var wv = Module.findExportByName("libc.so", "writev");
    Interceptor.attach(wv, {
      onEnter: function (a) { this.iov = a[1]; this.cnt = a[2].toInt32(); },
      onLeave: function () {
        try {
          for (var i = 0; i < this.cnt; i++) {
            var base = this.iov.add(i * 16).readPointer();
            var len = this.iov.add(i * 16 + 8).readU64().toNumber();
            check(base, len, "W-writev[" + i + "]");
          }
        } catch (e) {}
      }
    });
    console.log("[hook36] writev @ " + wv);
  } catch (e) { console.log("[hook36] writev fail " + e.message); }
  try {
    var sm = Module.findExportByName("libc.so", "sendmsg");
    Interceptor.attach(sm, {
      onEnter: function (a) { this.msg = a[1]; },
      onLeave: function () {
        try {
          var iov = this.msg.add(0x10).readPointer();
          var cnt = this.msg.add(0x18).readU64().toNumber();
          for (var i = 0; i < cnt && i < 8; i++) {
            var base = iov.add(i * 16).readPointer();
            var len = iov.add(i * 16 + 8).readU64().toNumber();
            check(base, len, "W-sendmsg[" + i + "]");
          }
        } catch (e) {}
      }
    });
    console.log("[hook36] sendmsg @ " + sm);
  } catch (e) { console.log("[hook36] sendmsg fail " + e.message); }
  armed = true;
}

arm();
setInterval(arm, 2000);

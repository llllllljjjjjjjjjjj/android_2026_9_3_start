/**
 * 定制版 r0capture script.js —— 抖音 TTNet/cronet 抓包
 * 改动：
 *   1. hook 目标库 = 抖音自带 *libttboringssl*（原版写死系统 *libssl*）
 *   2. libttboringssl 由 libsscronet 运行期按需加载 —— 冷启早期尚未映射，
 *      故用轮询 waitUntilLoaded() 延迟安装 uprobe，等模块出现后再 attach
 * 其余逻辑与原版 r0ysue/r0capture 一致。
 */
"use strict";

var addresses = {};
var SSL_get_fd = null;
var SSL_get_session = null;
var SSL_SESSION_get_id = null;
var ntohs = null;
var ntohl = null;
var installed = false;

var libname = "*libttboringssl*";

function return_zero(args) { return 0; }

function ipToNumber(ip) {
  var num = 0;
  if (ip == "") return num;
  var aNum = ip.split(".");
  if (aNum.length != 4) return num;
  num += parseInt(aNum[0]) << 24;
  num += parseInt(aNum[1]) << 16;
  num += parseInt(aNum[2]) << 8;
  num += parseInt(aNum[3]);
  num = num >>> 0;
  return num;
}

function resolveSymbols() {
  var resolver = new ApiResolver("module");
  var exps = [
    [libname, ["SSL_read", "SSL_write", "SSL_get_fd", "SSL_get_session", "SSL_SESSION_get_id"]],
    ["*libc*", ["getpeername", "getsockname", "ntohs", "ntohl"]]
  ];
  for (var i = 0; i < exps.length; i++) {
    var lib = exps[i][0];
    var names = exps[i][1];
    for (var j = 0; j < names.length; j++) {
      var name = names[j];
      var matches = resolver.enumerateMatches("exports:" + lib + "!" + name);
      if (matches.length == 0) {
        if (name == "SSL_get_fd") { addresses["SSL_get_fd"] = 0; continue; }
        throw new Error("Could not find " + lib + "!" + name);
      }
      var sel = matches[0];
      for (var k = 0; k < matches.length; k++) {
        if (matches[k].name.indexOf("libttboringssl") !== -1) { sel = matches[k]; break; }
      }
      addresses[name] = sel.address;
      console.log("[*] " + name + " <- " + sel.name + " @ " + sel.address);
    }
  }
}

function install() {
  if (installed) return;
  try {
    resolveSymbols();
  } catch (e) {
    console.log("[wait] " + e.message + " (retry 1000ms)");
    return;
  }
  SSL_get_fd = addresses["SSL_get_fd"] == 0 ? return_zero
      : new NativeFunction(addresses["SSL_get_fd"], "int", ["pointer"]);
  SSL_get_session = new NativeFunction(addresses["SSL_get_session"], "pointer", ["pointer"]);
  SSL_SESSION_get_id = new NativeFunction(addresses["SSL_SESSION_get_id"], "pointer", ["pointer", "pointer"]);
  ntohs = new NativeFunction(addresses["ntohs"], "uint16", ["uint16"]);
  ntohl = new NativeFunction(addresses["ntohl"], "uint32", ["uint32"]);

  function getPortsAndAddresses(sockfd, isRead) {
    var message = {};
    var src_dst = ["src", "dst"];
    for (var i = 0; i < src_dst.length; i++) {
      var sockAddr = (src_dst[i] == "src") ^ isRead ? Socket.localAddress(sockfd) : Socket.peerAddress(sockfd);
      if (sockAddr == null) {
        message[src_dst[i] + "_port"] = 0;
        message[src_dst[i] + "_addr"] = 0;
      } else {
        message[src_dst[i] + "_port"] = (sockAddr.port & 0xFFFF);
        message[src_dst[i] + "_addr"] = ntohl(ipToNumber(sockAddr.ip.split(":").pop()));
      }
    }
    return message;
  }

  function getSslSessionId(ssl) {
    var session = SSL_get_session(ssl);
    if (session == 0) return 0;
    var len = Memory.alloc(4);
    var p = SSL_SESSION_get_id(session, len);
    len = len.readU32();
    var s = "";
    for (var i = 0; i < len; i++) s += ("0" + p.add(i).readU8().toString(16).toUpperCase()).slice(-2);
    return s;
  }

  Interceptor.attach(addresses["SSL_read"], {
    onEnter: function (args) {
      var m = getPortsAndAddresses(SSL_get_fd(args[0]), true);
      m["ssl_session_id"] = getSslSessionId(args[0]);
      m["function"] = "SSL_read";
      this.m = m; this.buf = args[1];
    },
    onLeave: function (retval) {
      retval |= 0;
      if (retval <= 0) return;
      send(this.m, this.buf.readByteArray(retval));
    }
  });

  Interceptor.attach(addresses["SSL_write"], {
    onEnter: function (args) {
      var m = getPortsAndAddresses(SSL_get_fd(args[0]), false);
      m["ssl_session_id"] = getSslSessionId(args[0]);
      m["function"] = "SSL_write";
      send(m, args[1].readByteArray(parseInt(args[2])));
    },
    onLeave: function (retval) { }
  });

  installed = true;
  console.log("[*] installed hooks on libttboringssl");
}

function waitUntilLoaded() {
  install();
  if (!installed) setTimeout(waitUntilLoaded, 1000);
}
setTimeout(waitUntilLoaded, 1000);

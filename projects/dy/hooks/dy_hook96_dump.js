// dy_hook96_dump.js — dump 指定地址 512KB（RPC dump(addr)）
rpc.exports = {
  dump: function (addrStr) {
    var p = ptr(addrStr);
    try {
      var s = p.readUtf8String(524288);
      return s;
    } catch (e) {
      return "ERR " + e.message;
    }
  }
};
send({ t: "ready", m: "hook96 loaded" });

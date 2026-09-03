// dy_hook100_openimg.js — 扫 open_image/close_image/authorization 上下文 dump 256KB
var DONE = false;
var RESULTS = [];

function scanOnce() {
  if (DONE) return RESULTS;
  var pats = [
    "6f 70 65 6e 5f 69 6d 61 67 65",        // open_image
    "63 6c 6f 73 65 5f 69 6d 61 67 65",    // close_image
    "61 75 74 68 6f 72 69 7a 61 74 69 6f 6e", // authorization
    "62 72 61 6e 64 5f 61 75 74 68"         // brand_auth
  ];
  var ranges = Process.enumerateRanges("r--");
  var sent = {};
  ranges.forEach(function (r) {
    if (r.size < 4096 || r.size > 512 * 1024 * 1024) return;
    pats.forEach(function (pat) {
      var res;
      try { res = Memory.scanSync(r.base, r.size, pat); } catch (e) { return; }
      var cnt = 0;
      res.forEach(function (m) {
        if (cnt >= 4 || RESULTS.length >= 10) return;
        cnt++;
        try {
          var p = m.address, start = null;
          for (var i = 0; i < 16384; i++) {
            var q = p.sub(i);
            try { if (q.readU8() === 0x7b) { start = q; break; } } catch (e) { break; }
          }
          if (!start) return;
          var key = start.toString();
          if (sent[key]) return;
          sent[key] = true;
          var s = start.readUtf8String(262144);
          send({ t: "ctx", addr: start.toString(), body: s });
          RESULTS.push(start.toString());
        } catch (e) {}
      });
    });
  });
  DONE = true;
  return RESULTS;
}

rpc.exports = {
  scan: scanOnce,
  count: function () { return RESULTS.length; }
};
send({ t: "ready", m: "hook100 loaded" });

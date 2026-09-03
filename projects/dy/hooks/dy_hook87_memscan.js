// dy_hook87_memscan.js — 内存扫描电商详情响应 JSON（产品参数/品牌资质）
// 详情响应由 libsscronet native nlohmann/json 解析，Java hook 抓不到。
// 定时扫 "qualification" / "brand_info" / "spec_info" / "product_params" 字符串，
// 回溯 JSON 开头 '{'，dump 40KB 片段 send 回 PC（落盘 capture/memscan_*.txt）。
var PATS = [
  "71 75 61 6c 69 66 69 63 61 74 69 6f 6e",  // qualification
  "62 72 61 6e 64 5f 69 6e 66 6f",          // brand_info
  "73 70 65 63 5f 69 6e 66 6f",             // spec_info
  "70 72 6f 64 75 63 74 5f 70 61 72 61 6d 73", // product_params
  "62 72 61 6e 64 5f 71 75 61 6c"           // brand_qual
];
var sent = {};
var scanCount = 0;

function tryDump(m) {
  try {
    var p = m.address;
    var start = p;
    for (var i = 0; i < 4096; i++) {
      var q = p.sub(i);
      try { if (q.readU8() === 0x7b) { start = q; break; } } catch (e) { break; }
    }
    var s = start.readUtf8String(40000);
    // 校验含关键词与结构完整性（粗略）
    if (s.indexOf("qualification") < 0 && s.indexOf("brand") < 0 && s.indexOf("spec") < 0) return;
    var key = start.toString() + ":" + s.slice(0, 80);
    if (sent[key]) return;
    sent[key] = true;
    send({ t: "json", addr: start.toString(), body: s });
  } catch (e) {}
}

function scan() {
  scanCount++;
  var ranges = Process.enumerateRanges("r--");
  ranges.forEach(function (r) {
    if (r.size < 4096 || r.size > 512 * 1024 * 1024) return;
    PATS.forEach(function (pat) {
      var res;
      try { res = Memory.scanSync(r.base, r.size, pat); } catch (e) { return; }
      var cnt = 0;
      res.forEach(function (m) {
        if (cnt >= 3) return;  // 每区域每模式最多 3 个
        cnt++;
        tryDump(m);
      });
    });
  });
}

setInterval(scan, 2500);
send({ t: "ready", m: "hook87 memscan armed" });

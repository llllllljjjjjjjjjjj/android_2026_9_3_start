// dy_hook_detail_param.js — RPC 返回商品详情页产品参数（attr 字段）
//
// detail/stream 响应由 libsscronet native nlohmann/json 解析，Java hook 抓不到；
// 响应原始 JSON（或转义内嵌形式）在内存里以 qualification 锚点回溯可达
// （见 hook90/93 实证，detail_ctx.json 即此产物）。
// 本 hook 扫描 qualification 锚点 → 回溯 '{' → 读大片段 → 反转义提取
// attr_id / title / property_name_all / value。
//
// RPC（方法名全小写，frida 16.5.7 Python 绑定 lower() 查找）：
//   mark()    记录当前已见为基线（打开详情页前调用）
//   new()     返回 mark 之后新出现的产品参数对象
//   scanall() 返回全部已见
//   reset()   清空
var PAT_QUAL = "71 75 61 6c 69 66 69 63 61 74 69 6f 6e"; // qualification
var seen = {};
var baseline = {};
var order = [];
var scanBusy = false;

function unesc(s) {
  return s.replace(/\\"/g, '"').replace(/\\\\/g, '\\');
}

function extract(t) {
  var g = function (re) {
    var m = t.match(re);
    return m ? m[1] : "";
  };
  return {
    attr_id: g(/"attr_id":"([^"]*)"/),
    title: g(/"title":"([^"]*)"/),
    names: g(/"property_name_all":"([^"]*)"/),
    values: g(/"value":"([^"]*)"/)
  };
}

function tryDump(m) {
  try {
    var start = null;
    for (var i = 0; i < 16384; i++) {
      var q = m.address.sub(i);
      try {
        if (q.readU8() === 0x7b) { start = q; break; }
      } catch (e) { break; }
    }
    if (!start) return;
    var s = start.readUtf8String(200000);
    // 明文或转义形式都要覆盖
    var hasPlain = s.indexOf('"property_name_all"') >= 0;
    var hasEsc = s.indexOf('\\"property_name_all\\"') >= 0;
    if (!hasPlain && !hasEsc) return;
    var a = extract(unesc(s));
    if (!a.names || !a.values || !a.attr_id) return;
    var key = a.attr_id + "|" + a.values;
    if (seen[key]) return;
    seen[key] = a;
    order.push(key);
    send({ t: "param", attr_id: a.attr_id, title: a.title });
  } catch (e) {}
}

function scan() {
  if (scanBusy) return;
  scanBusy = true;
  try {
    var ranges = Process.enumerateRanges("r--");
    ranges.forEach(function (r) {
      try {
        if (r.size < 4096 || r.size > 512 * 1024 * 1024) return;
        var res = Memory.scanSync(r.base, r.size, PAT_QUAL);
        var cnt = 0;
        res.forEach(function (m) {
          if (cnt >= 3) return;
          cnt++;
          tryDump(m);
        });
      } catch (e) {}
    });
  } finally {
    scanBusy = false;
  }
}

setInterval(scan, 1200);
scan();

rpc.exports = {
  mark: function () {
    baseline = {};
    var k;
    for (k in seen) baseline[k] = true;
    return Object.keys(baseline).length;
  },
  new: function () {
    var out = [];
    for (var i = 0; i < order.length; i++) {
      var k = order[i];
      if (!baseline[k] && seen[k]) out.push(seen[k]);
    }
    return out;
  },
  scanall: function () {
    var out = [];
    for (var i = 0; i < order.length; i++) out.push(seen[order[i]]);
    return out;
  },
  reset: function () {
    seen = {};
    baseline = {};
    order = [];
    return "reset";
  }
};
send({ t: "ready", m: "detail_param memscan armed (qualification)" });

// dy_hook41_json_topdown.js — 顶层 JSON 解析 hook（SF-002 头条案例正解路线）
// 搜索响应解码后必然进入 JSON 解析；按响应特征键过滤截获完整 JSON。
// 兼容 org.json 与 bytedance JSON（多路径尝试）
function tryHookJsonObject() {
  var hooked = 0;
  var cands = [
    ["org.json.JSONObject", "org.json.JSONObject"],
    ["com.bytedance.mt.protocol.impl.json.JSONObject", "com.bytedance.mt.protocol.impl.json.JSONObject"]
  ];
  cands.forEach(function (c) {
    var clsName = c[0];
    try {
      var C = Java.use(clsName);
      var ctors = C.$init.overloads;
      ctors.forEach(function (ov) {
        var argTypes = ov.argumentTypes.map(function (t) { return t.className; }).join(",");
        if (argTypes.indexOf("java.lang.String") !== -1 && argTypes.split(",").length === 1) {
          ov.implementation = function (str) {
            try {
              var s = str + "";
              if (s.length > 50 && /business_data|search_result|"struct"|"aweme_info"/.test(s)) {
                send({ t: "json", cls: clsName, len: s.length, head: s.slice(0, 600) });
              }
            } catch (e) {}
            return ov.call(this, str);
          };
          hooked++;
        }
      });
      if (hooked) console.log("[json] hooked " + clsName + " ctors=" + hooked);
    } catch (e) {
      // 类不存在则跳过
    }
  });
  return hooked;
}

Java.perform(function () {
  var n = tryHookJsonObject();
  if (n === 0) console.log("[json] no JSONObject ctor hooked");
  else console.log("[json] total hooked=" + n);
});

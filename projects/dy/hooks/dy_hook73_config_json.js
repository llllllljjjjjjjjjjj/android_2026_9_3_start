// dy_hook73_config_json.js — hook org.json 抓含 dict/zstd 的 config JSON
Java.perform(function () {
  ["org.json.JSONObject", "org.json.JSONTokener"].forEach(function (cn) {
    try {
      var C = Java.use(cn);
      C.$init.overloads.forEach(function (ov) {
        if (ov.argumentTypes.map(function (t) { return t.className; }).join(",") === "java.lang.String") {
          ov.implementation = function (s) {
            var str = String(s);
            if (/dict|zstd|ttzip/i.test(str) && str.length < 100000) {
              console.log("[CONFIG-JSON] " + str.slice(0, 800));
            }
            return ov.call(this, s);
          };
        }
      });
    } catch (e) {}
  });
});
console.log("[hook73] loaded");

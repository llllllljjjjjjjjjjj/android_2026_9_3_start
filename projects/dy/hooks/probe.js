"use strict";
// 探测 dy 搜索进程网络层 hook 点
setImmediate(function () {
  try {
    var mods = Process.enumerateModules().filter(function (m) {
      return /sscronet|ttboringssl|ttnet|cronet|okhttp|aweme.*net|metasec/i.test(m.name);
    });
    mods.forEach(function (m) { console.log("MOD " + m.name + " @ " + m.base); });
    console.log("MOD_COUNT " + mods.length);
  } catch (e) { console.log("MOD_ERR " + e); }
});

if (Java.available) {
  Java.perform(function () {
    var cls = [
      "okhttp3.Request", "okhttp3.Interceptor", "okhttp3.HttpUrl",
      "com.bytedance.retrofit2.Retrofit", "com.bytedance.retrofit2.RequestBuilder",
      "com.bytedance.frameworks.baselib.network.http.cronet.ICronetClient",
      "com.bytedance.frameworks.baselib.network.http.cronet.ICronetAppProvider",
      "com.bytedance.ies.ugc.aweme.network.IRetrofit",
      "com.bytedance.retrofit2.okhttp.OkHttpCall"
    ];
    cls.forEach(function (c) {
      try {
        var clz = Java.use(c);
        console.log("JAVA+ " + c);
      } catch (e) {
        console.log("JAVA- " + c + " :: " + String(e).slice(0, 60));
      }
    });
  });
}

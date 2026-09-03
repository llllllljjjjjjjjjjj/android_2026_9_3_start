// dy_hook40_java_scan.js — 顶层侦察：枚举 Java 搜索相关类 + 找响应处理入口
Java.perform(function () {
  var hits = [];
  Java.enumerateLoadedClasses({
    onMatch: function (name) {
      if (/search/i.test(name) && !/annotation|interceptor|databinding/i.test(name)) {
        if (/repository|presenter|service|api|manager|model|viewmodel|consumer|callback/i.test(name) ||
            /Search.*Result|Result.*Search/i.test(name)) {
          hits.push(name);
          if (hits.length <= 60) console.log("[cls] " + name);
        }
      }
    },
    onComplete: function () {
      console.log("[scan] search-related classes total=" + hits.length);
    }
  });
});

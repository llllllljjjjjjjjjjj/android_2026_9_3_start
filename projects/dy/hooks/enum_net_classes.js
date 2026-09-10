"use strict";
// 枚举已加载的网络实现类，定位请求头组装/发送点
Java.perform(function () {
  var found = [];
  var re = /(cronet|ttnet|network\.http|okhttp3\.internal|Retrofit|NetworkParams|CommonParam)/i;
  Java.enumerateLoadedClasses({
    onMatch: function (name) {
      if (re.test(name) && found.length < 120) {
        found.push(name);
      }
    },
    onComplete: function () {
      found.sort();
      found.forEach(function (n) { console.log("CLS " + n); });
      console.log("TOTAL " + found.length);
    }
  });
});

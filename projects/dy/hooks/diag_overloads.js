"use strict";
Java.perform(function () {
  var RB = Java.use("com.bytedance.retrofit2.RequestBuilder");
  console.log("=== RB.build overloads: " + RB.build.overloads.length);
  RB.build.overloads.forEach(function (o, i) {
    console.log("  [" + i + "] " + o.argumentTypes.map(function (t) { return t.className; }).join(", ") + " -> " + o.returnType.className);
  });
  console.log("=== RB.addHeader overloads: " + RB.addHeader.overloads.length);
  RB.addHeader.overloads.forEach(function (o, i) {
    console.log("  [" + i + "] " + o.argumentTypes.map(function (t) { return t.className; }).join(", "));
  });
  console.log("=== RB.addQueryParam overloads: " + RB.addQueryParam.overloads.length);
  RB.addQueryParam.overloads.forEach(function (o, i) {
    console.log("  [" + i + "] " + o.argumentTypes.map(function (t) { return t.className; }).join(", "));
  });
});

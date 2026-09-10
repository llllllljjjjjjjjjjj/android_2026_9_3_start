"use strict";
// 通用代理 hook ChunkDataStream.subscribe —— 拦截任意 chunk 类型 T 的 onNext
// 安全：只在低频 subscribe 时建代理，onNext 内仅做 toString（不构造 JSONObject）
var n = 0;

Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }

  try {
    var CDS = Java.use("com.bytedance.android.chunkstreamprediction.network.ChunkDataStream");
    var Obs = Java.use("com.bytedance.android.chunkstreamprediction.network.ChunkDataObserver");

    CDS.subscribe.implementation = function (observer) {
      n++;
      var tag = n;
      console.log("@@ subscribe #" + tag);
      try {
        var ProxyClass = Java.registerClass({
          name: "com.dy.obs.Proxy" + tag,
          implements: [Obs],
          methods: {
            onNext: function (t) {
              try {
                var cn = t ? t.getClass().getName() : "null";
                var s = t ? String(t.toString()) : "";
                console.log("@@CHUNK#" + tag + " cls=" + cn + " len=" + s.length);
                console.log("@@CHUNKDATA " + s.slice(0, 2500));
              } catch (e) { console.log("@@chunk err " + S(e)); }
              try { return observer.onNext(t); } catch (e2) { return null; }
            },
            onComplete: function () {
              console.log("@@ complete #" + tag);
              try { return observer.onComplete(); } catch (e) { return null; }
            },
            onFailed: function (th) {
              console.log("@@ failed #" + tag + " " + S(th));
              try { return observer.onFailed(th); } catch (e) { return null; }
            }
          }
        });
        var p = ProxyClass.$new();
        return this.subscribe(p);
      } catch (e) {
        console.log("@@ proxy err " + S(e));
        return this.subscribe(observer);
      }
    };
    console.log("@@ hooked ChunkDataStream.subscribe (proxy)");
  } catch (e) { console.log("@@ CDS err " + S(e)); }
});

"use strict";
// 决定性诊断：dump CommentItemList 的完整 JSON + 打印所有 chunk 类型
Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }
  var dumped = 0, chunkN = 0;

  try {
    var CDS = Java.use("com.bytedance.android.chunkstreamprediction.network.ChunkDataStream");
    var Obs = Java.use("com.bytedance.android.chunkstreamprediction.network.ChunkDataObserver");
    var idx = 0;
    CDS.subscribe.implementation = function (observer) {
      idx++;
      var tag = idx;
      try {
        var Proxy = Java.registerClass({
          name: "com.dy.dg.P" + tag,
          implements: [Obs],
          methods: {
            onNext: function (t) {
              try {
                if (t) {
                  var cn = S(t.getClass().getName());
                  chunkN++;
                  console.log("@@CHUNK[" + chunkN + "] " + cn);
                  if (cn.indexOf("CommentItemList") >= 0 && dumped < 2) {
                    dumped++;
                    var Gson = Java.use("com.google.gson.Gson");
                    var js = String(Gson.$new().toJson(t));
                    console.log("@@FULLJSON len=" + js.length);
                    console.log("@@FULL " + JSON.stringify(js.slice(0, 2500)));
                  }
                }
              } catch (e) { console.log("@@e " + S(e)); }
              try { return observer.onNext(t); } catch (e2) { return null; }
            },
            onComplete: function () { try { return observer.onComplete(); } catch (e) { return null; } },
            onFailed: function (th) { try { return observer.onFailed(th); } catch (e) { return null; } }
          }
        });
        return this.subscribe(Proxy.$new());
      } catch (e) { return this.subscribe(observer); }
    };
    console.log("@@ hooked (full dump)");
  } catch (e) { console.log("@@ err " + S(e)); }
});

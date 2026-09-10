"use strict";
// 定位 chunk 解密/解析：hook ChunkDataStream 的 Operation 回调 + onNext 前的数据来源
// 思路：加密 chunk → 明文对象必然有一次「字节 → 对象」的转换
//       先枚举 chunkstreamprediction 与 netx.chunk 包的关键类是否已加载
Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }

  var pats = ["ChunkDataStream", "ChunkDataObserver", "ChunkDataException",
              "NetXChunkHandler", "ChunkStateMachine", "LiveNetXChunkInterceptor",
              "ChunkStreamDefaultThreadExecutor", "InterruptibleDrawingViewHelper"];

  Java.enumerateLoadedClasses({
    onMatch: function (name) {
      for (var i = 0; i < pats.length; i++) {
        if (name.indexOf(pats[i]) >= 0) { console.log("@@LOADED " + name); return; }
      }
      if (name.indexOf("chunk") >= 0 || name.indexOf("Chunk") >= 0) {
        console.log("@@CHUNKCLS " + name);
      }
    },
    onComplete: function () { console.log("@@ enum done"); }
  });
});

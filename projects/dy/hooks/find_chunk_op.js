"use strict";
// 定位 chunk 解密点：hook ChunkDataStream 构造函数，抓 Operation 实现类名
var ops = {};
var opObj = null;

Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }

  try {
    var CDS = Java.use("com.bytedance.android.chunkstreamprediction.network.ChunkDataStream");
    var OpIface = Java.use("com.bytedance.android.chunkstreamprediction.network.ChunkDataStream$Operation");
    var ctor = CDS.$init.overload("com.bytedance.android.chunkstreamprediction.network.ChunkDataStream$Operation");
    ctor.implementation = function (op) {
      try {
        var cn = "null";
        try {
          cn = String(Java.cast(op, Java.use("java.lang.Object")).getClass().getName());
        } catch (e0) {
          try { cn = String(op.toString()); } catch (e1) { cn = "<unknown>"; }
        }
        if (!ops[cn]) {
          ops[cn] = 0;
          opObj = op;
          console.log("@@OPCLASS " + cn);
          try {
            var cls = Java.cast(op, Java.use("java.lang.Object")).getClass();
            var ms = cls.getDeclaredMethods();
            var names = [];
            for (var i = 0; i < ms.length && i < 40; i++) {
              var ps = ms[i].getParameterTypes();
              var pn = [];
              for (var k = 0; k < ps.length; k++) pn.push(ps[k].getSimpleName());
              names.push(ms[i].getName() + "(" + pn.join(",") + ")");
            }
            console.log("@@OPMETHODS " + names.join(" | "));
          } catch (e) { console.log("@@ meth err " + S(e)); }
        }
        ops[cn]++;
      } catch (e) { console.log("@@ err " + S(e)); }
      return ctor.call(this, op);
    };
    console.log("@@ hooked ChunkDataStream ctor");
  } catch (e) { console.log("@@ hook err " + S(e)); }

  rpc.exports = {
    ops: function () { return ops; },
    callop: function () {
      // 手动触发 Operation.call（诊断用）
      var r = 0;
      try {
        if (opObj) { r = 1; }
      } catch (e) { }
      return r;
    }
  };
});

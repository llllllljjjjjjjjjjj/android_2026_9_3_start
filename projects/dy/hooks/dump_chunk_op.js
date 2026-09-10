"use strict";
// 直接 dump chunk Operation 实现（X.18wv）的所有字段与方法签名
var opRef = null;

Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }

  try {
    var CDS = Java.use("com.bytedance.android.chunkstreamprediction.network.ChunkDataStream");
    var ctor = CDS.$init.overload("com.bytedance.android.chunkstreamprediction.network.ChunkDataStream$Operation");
    ctor.implementation = function (op) {
      try {
        if (!opRef) {
          opRef = op;
          var obj = Java.cast(op, Java.use("java.lang.Object"));
          var cls = obj.getClass();
          console.log("@@OPNAME " + cls.getName());

          // 全部字段（含类型）
          try {
            var fs = cls.getDeclaredFields();
            for (var i = 0; i < fs.length; i++) {
              console.log("@@OPFIELD " + fs[i].getName() + " : " + fs[i].getType().getName());
            }
          } catch (e) { }

          // 全部方法（含参数）
          try {
            var ms = cls.getDeclaredMethods();
            for (var j = 0; j < ms.length; j++) {
              var ps = ms[j].getParameterTypes();
              var pn = [];
              for (var k = 0; k < ps.length; k++) pn.push(ps[k].getName());
              console.log("@@OPM " + ms[j].getName() + "(" + pn.join(", ") + ")");
            }
          } catch (e) { }

          // 父类/接口
          try {
            var sup = cls.getSuperclass();
            if (sup) console.log("@@OPSUPER " + sup.getName());
            var ifs = cls.getInterfaces();
            for (var m = 0; m < ifs.length; m++) console.log("@@OPIFACE " + ifs[m].getName());
          } catch (e) { }

          // 静态字段的值（可能含 decoder 实例）
          try {
            var fs2 = cls.getDeclaredFields();
            for (var n = 0; n < fs2.length; n++) {
              try {
                var mod = fs2[n].getModifiers();
                if ((mod & 0x0008) !== 0) {   // static
                  fs2[n].setAccessible(true);
                  var v = fs2[n].get(null);
                  console.log("@@OPSTATIC " + fs2[n].getName() + " = " +
                    (v === null ? "null" : (S(v.getClass().getName()) || String(v).slice(0, 60))));
                }
              } catch (e2) { }
            }
          } catch (e) { }
        }
      } catch (e) { console.log("@@ err " + S(e)); }
      return ctor.call(this, op);
    };
    console.log("@@ hooked (op dump)");
  } catch (e) { console.log("@@ hook err " + S(e)); }

  rpc.exports = {
    has: function () { return !!opRef; }
  };
});

"use strict";
// 诊断 RPC: ClientKeyManager / MSManager 的运行时方法与实例状态
Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }
  var out = {};

  function methodsOf(cn) {
    try {
      var C = Java.use(cn);
      var ms = C.class.getDeclaredMethods();
      var list = [];
      ms.forEach(function (m) {
        var mods = m.getModifiers();
        var isStatic = (mods & 0x0008) !== 0;
        if (isStatic) {
          list.push(m.getName() + "(" + m.getParameterTypes().map(function (t) { return t.getName().split(".").pop(); }).join(",") + ")");
        }
      });
      return list;
    } catch (e) { return ["ERR " + S(e)]; }
  }

  out.ckm_static = methodsOf("com.bytedance.ttnet.clientkey.ClientKeyManager");
  out.msm_static = methodsOf("com.bytedance.mobsec.metasec.ml.MSManagerUtils");
  out.msb_static = methodsOf("com.bytedance.mobsec.metasec.ml.MSB");

  // 直接尝试调用
  try {
    var CK = Java.use("com.bytedance.ttnet.clientkey.ClientKeyManager");
    var h = CK.getClientKeyHeaders();
    out.ck_call = h ? "OK size=" + h.size() : "null";
  } catch (e) { out.ck_call_err = S(e); }

  console.log(JSON.stringify(out, null, 1));
});

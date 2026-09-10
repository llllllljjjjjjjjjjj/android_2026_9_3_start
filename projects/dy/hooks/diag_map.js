"use strict";
Java.perform(function () {
  var rep = {};
  try {
    var CK = Java.use("com.bytedance.ttnet.clientkey.ClientKeyManager");
    var m = CK.getClientKeyHeaders();
    rep.step1_got = (m !== null);
    try { rep.cls = m.getClass().getName(); } catch (e) { rep.cls_err = String(e); }
    try { rep.size = m.size(); } catch (e) { rep.size_err = String(e); }
    try { rep.tostring = String(m); } catch (e) { rep.tostring_err = String(e); }
    try { var ks = m.keySet(); rep.keyset = String(ks) + " size=" + ks.size(); } catch (e) { rep.keyset_err = String(e); }
    try { var es = m.entrySet(); rep.entryset = "ok size=" + es.size(); } catch (e) { rep.entryset_err = String(e); }
    try {
      var es2 = m.entrySet();
      var it = es2.iterator();
      rep.iter = "ok hasNext=" + it.hasNext();
      var e1 = it.next();
      rep.e1 = "ok";
      try { rep.e1_key = String(e1.getKey()); } catch (e) { rep.e1_key_err = String(e); }
      try { rep.e1_val = String(e1.getValue()).slice(0, 60); } catch (e) { rep.e1_val_err = String(e); }
    } catch (e) { rep.iter_err = String(e); }
    // 尝试 Java 层 JSONObject(Map)
    try {
      var JO = Java.use("org.json.JSONObject");
      var jo = JO.$new(m);
      rep.json = String(jo.toString()).slice(0, 400);
    } catch (e) { rep.json_err = String(e); }
  } catch (e) { rep.outer_err = String(e); }
  console.log("DIAG " + JSON.stringify(rep, null, 1));
});

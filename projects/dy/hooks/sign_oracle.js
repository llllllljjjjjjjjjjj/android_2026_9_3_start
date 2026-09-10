"use strict";
// dy signature RPC oracle
// targets: 1) MSManager.frameSign(scene,mode) -> MS signature headers
//          2) ClientKeyManager.getClientKeyHeaders() -> x-tt-token headers
// NOTE: frida Python RPC method names must be all lowercase.
// NOTE: rpc callbacks run on the JS thread with Java already initialized -> call Java API directly.
var msInstance = null;
var lastFrameSignArgs = null;

function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }

function mapToObj(m) {
  if (!m) return null;
  // Map.Entry getters are unavailable in this frida build -> use Java-layer JSONObject(Map)
  try {
    var JO = Java.use("org.json.JSONObject");
    var jo = JO.$new(m);
    return JSON.parse(String(jo.toString()));
  } catch (e) {
    return { _err: String(e) };
  }
}

Java.perform(function () {
  try {
    var MSManager = Java.use("com.bytedance.mobsec.metasec.ml.MSManager");
    MSManager.frameSign.implementation = function (str, i) {
      msInstance = this;
      lastFrameSignArgs = { scene: S(str), mode: i };
      console.log("[frameSign called] scene=" + S(str) + " mode=" + i);
      var r = this.frameSign(str, i);
      try { console.log("  -> " + JSON.stringify(mapToObj(r))); } catch (e) { }
      return r;
    };
    console.log("[*] hooked MSManager.frameSign");
  } catch (e) { console.log("MSManager err " + S(e)); }

  try {
    var MSManager2 = Java.use("com.bytedance.mobsec.metasec.ml.MSManager");
    MSManager2.getToken.implementation = function () {
      var t = this.getToken();
      console.log("[getToken] " + S(t).slice(0, 120));
      return t;
    };
  } catch (e) { }

  rpc.exports = {
    clientkeyheaders: function () {
      return new Promise(function (resolve) {
        Java.perform(function () {
          try {
            var CK = Java.use("com.bytedance.ttnet.clientkey.ClientKeyManager");
            resolve(mapToObj(CK.getClientKeyHeaders()));
          } catch (e) { resolve({ _err: S(e) }); }
        });
      });
    },
    framesign: function (scene, mode) {
      return new Promise(function (resolve) {
        Java.perform(function () {
          try {
            if (!msInstance) { resolve({ _err: "no MSManager instance yet (trigger a search first)" }); return; }
            resolve(mapToObj(msInstance.frameSign(scene, mode)));
          } catch (e) { resolve({ _err: S(e) }); }
        });
      });
    },
    mstoken: function () {
      return new Promise(function (resolve) {
        Java.perform(function () {
          try {
            if (!msInstance) { resolve({ _err: "no instance" }); return; }
            resolve(S(msInstance.getToken()));
          } catch (e) { resolve({ _err: S(e) }); }
        });
      });
    },
    state: function () {
      return { hasInstance: !!msInstance, lastArgs: lastFrameSignArgs };
    }
  };
  console.log("[*] rpc exports ready");
});

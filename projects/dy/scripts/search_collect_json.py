# -*- coding: utf-8 -*-
# search_collect_json.py v2 — 顶层 JSON 采集器（org.json + fastjson + gson 全覆盖）
import argparse
import json
import subprocess
import time
from pathlib import Path

import frida

ROOT = Path(__file__).resolve().parents[1]
ADB = r"D:\reserve_agent\skills-portable-test\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
OUT = ROOT / "capture" / "search_json_capture.jsonl"

JS = r'''
Java.perform(function () {
  function keep(s) {
    return (/search_keyword|search_result_id|business_data|"aweme_info"|general_search|"raw_data"/.test(s) &&
            s.length > 100 && s.length < 500000);
  }
  function rep(cls, m, s) {
    try { send({ t: "j", cls: cls, m: m, len: s.length, body: s }); } catch (e) {}
  }
  ["org.json.JSONObject", "org.json.JSONTokener"].forEach(function (cn) {
    try {
      var C = Java.use(cn);
      C.$init.overloads.forEach(function (ov) {
        if (ov.argumentTypes.map(function (t) { return t.className; }).join(",") === "java.lang.String") {
          ov.implementation = function (s) {
            try { if (keep(String(s))) rep(cn, "$init", String(s)); } catch (e) {}
            return ov.call(this, s);
          };
        }
      });
      console.log("[hook] " + cn);
    } catch (e) {}
  });
  try {
    var FJ = Java.use("com.alibaba.fastjson.JSON");
    FJ.parseObject.overloads.forEach(function (ov) {
      var at = ov.argumentTypes.map(function (t) { return t.className; }).join(",");
      if (at.indexOf("java.lang.String") === 0) {
        ov.implementation = function (s) {
          try { if (keep(String(s))) rep("fastjson", "parseObject", String(s)); } catch (e) {}
          return ov.call(this, s);
        };
      }
    });
    console.log("[hook] fastjson");
  } catch (e) {}
  try {
    var G = Java.use("com.google.gson.Gson");
    G.fromJson.overloads.forEach(function (ov) {
      var at = ov.argumentTypes.map(function (t) { return t.className; }).join(",");
      if (at.indexOf("java.lang.String") === 0) {
        ov.implementation = function (s) {
          try { if (keep(String(s))) rep("gson", "fromJson", String(s)); } catch (e) {}
          return ov.call(this, s);
        };
      }
    });
    console.log("[hook] gson");
  } catch (e) {}
});
'''


def main():
    global hits
    ap = argparse.ArgumentParser()
    ap.add_argument("--kws", default="美食,火锅,面食,烧烤")
    ap.add_argument("--duration", type=int, default=100)
    args = ap.parse_args()

    subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"])
    pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
    print("[*] attach pid=%d" % pid, flush=True)
    dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
    s = dev.attach(pid)
    sc = s.create_script(JS)
    outf = open(OUT, "w", encoding="utf-8")
    hits = 0

    def on_msg(msg, data):
        global hits
        p = msg.get("payload")
        if isinstance(p, dict) and p.get("t") == "j":
            hits += 1
            outf.write(json.dumps({"cls": p["cls"], "m": p["m"], "len": p["len"], "body": p["body"]},
                                  ensure_ascii=False) + "\n")
            outf.flush()
        elif isinstance(p, str) and p.startswith("[hook]"):
            print(p, flush=True)
        elif msg.get("type") == "error":
            print("[JS-ERR]", msg.get("description"), flush=True)

    sc.on("message", on_msg)
    sc.load()
    kws = [k.strip() for k in args.kws.split(",") if k.strip()]
    per = max(8, args.duration // max(1, len(kws)))
    print("[*] 采集器 v2 已挂载，依次触发: %s" % kws, flush=True)
    for kw in kws:
        subprocess.check_call([ADB, "shell", "am", "start", "-a", "android.intent.action.VIEW",
                               "-d", "snssdk1128://search?keyword=" + kw])
        print("[*] 搜索: %s （%ds）" % (kw, per), flush=True)
        time.sleep(per)
    print("[*] 完成, JSON 命中 %d 条 → %s" % (hits, OUT), flush=True)
    outf.close()
    s.detach()


if __name__ == "__main__":
    main()

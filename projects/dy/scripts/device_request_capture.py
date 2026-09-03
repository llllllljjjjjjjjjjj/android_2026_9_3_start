# -*- coding: utf-8 -*-
# device_request_capture.py v2 — 挂 hook38v2，取 App 真机构建的完整搜索请求
#   --watch N   持续观察 N 秒，保存每次 mainSearch（general/stream|single）请求
#   --once      取一次当前 mainSearch 后退出
import argparse
import base64
import json
import subprocess
import time
from pathlib import Path

import frida

ROOT = Path(__file__).resolve().parents[1]
ADB = r"D:\reserve_agent\skills-portable-test\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
HOOK = ROOT / "hooks" / "dy_hook38_device_request.js"
OUT = ROOT / "capture" / "device_main_search.json"

_script = None


def connect():
    global _script
    subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"])
    pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
    dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
    s = dev.attach(pid)
    _script = s.create_script(open(HOOK, encoding="utf-8").read())

    def on_msg(msg, data):
        p = msg.get("payload")
        if isinstance(p, dict):
            t = p.get("t")
            if t in ("req", "body", "info", "ready"):
                print(f"[{t}] {p.get('url', p.get('idx', p.get('m', '')))}", flush=True)
        elif msg.get("type") == "error":
            print("[JS-ERR]", msg.get("description"), flush=True)

    _script.on("message", on_msg)
    _script.load()
    time.sleep(2)


def main_search():
    global _script
    if _script is None:
        connect()
    d = _script.exports_sync.mainsearch()
    if not d or not d.get("url"):
        return None
    return {
        "url": d["url"],
        "headers": d.get("headers", ""),
        "body": base64.b64decode(d.get("bodyB64", "")) if d.get("bodyB64") else b"",
        "size": d.get("size", 0),
        "ts": d.get("ts", 0),
    }


def save(req, tag=""):
    rec = {"url": req["url"], "headers": req["headers"],
           "bodyB64": base64.b64encode(req["body"]).decode(),
           "size": req["size"], "ts": req["ts"]}
    OUT.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    print(f"[saved{tag}] {OUT}")
    print(f"[saved{tag}] url={req['url'][:120]}")
    print(f"[saved{tag}] body={req['size']}B headers_len={len(req['headers'])}B ts={req['ts']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--watch", type=int, default=120)
    args = ap.parse_args()

    connect()
    print("[*] hook38v2 已挂载 —— 请在 App 触发搜索（持续保存 general/stream 请求）", flush=True)
    if args.once:
        time.sleep(6)
        req = main_search()
        if req:
            save(req, "!")
        else:
            print("[!] 暂无 general/stream 请求，先触发一次搜索")
        return
    end = time.time() + args.watch
    last_ts = 0
    while time.time() < end:
        req = main_search()
        if req and req["ts"] != last_ts:
            save(req)
            last_ts = req["ts"]
        time.sleep(3)
    print("[*] 观察结束")


if __name__ == "__main__":
    main()

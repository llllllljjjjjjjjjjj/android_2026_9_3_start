# -*- coding: utf-8 -*-
"""大众点评 mtgsig 在线 oracle 采集器

用 frida 16.5.x 连接 florida-server(16.5.9)，spawn/attach com.dianping.v1，
加载 hooks/mtgsig_oracle.js，收集 send() 消息并落盘 JSONL。

用法:
  .venv-frida-16.5.7/Scripts/python.exe scripts/mtgsig_collect.py --spawn
  .venv-frida-16.5.7/Scripts/python.exe scripts/mtgsig_collect.py --attach
"""
import argparse
import json
import os
import sys
import time
import signal
import threading

import frida

PKG = "com.dianping.v1"
HOOK = os.path.join(os.path.dirname(__file__), "..", "hooks", "mtgsig_oracle.js")
OUT = os.path.join(os.path.dirname(__file__), "..", "capture", "mtgsig_samples.jsonl")


def on_message(message, data, f):
    if message.get("type") == "send":
        payload = message.get("payload")
        if isinstance(payload, dict):
            line = json.dumps(payload, ensure_ascii=False)
            print("[sample]", line[:300], flush=True)
            f.write(line + "\n")
            f.flush()
    elif message.get("type") == "log":
        print("[js]", message.get("payload"), flush=True)
    elif message.get("type") == "error":
        print("[JS error]", message.get("stack") or message.get("description"), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spawn", action="store_true", help="spawn 模式冷启动")
    ap.add_argument("--attach", action="store_true", help="attach 到已运行进程(按名, 可能被反枚举)")
    ap.add_argument("--pid", type=int, default=0, help="直接 attach 指定 pid (反枚举 App 用 adb pidof 拿 pid)")
    ap.add_argument("--timeout", type=int, default=120, help="采集秒数")
    args = ap.parse_args()

    hook_src = open(HOOK, "r", encoding="utf-8").read()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    device = frida.get_device_manager().add_remote_device("127.0.0.1:27042")

    if args.pid:
        session = device.attach(args.pid)
        print("[*] attached pid=%d (direct)" % args.pid)
    elif args.attach:
        try:
            pid = device.get_process(PKG).pid
            session = device.attach(pid)
            print("[*] attached pid=%d" % pid)
        except frida.ProcessNotFoundError:
            print("[!] process not found, try --spawn or --pid")
            sys.exit(1)
    else:
        pid = device.spawn([PKG])
        print("[*] spawned pid=%d" % pid)
        session = device.attach(pid)

    script = session.create_script(hook_src)
    f = open(OUT, "a", encoding="utf-8")
    script.on("message", lambda msg, data: on_message(msg, data, f))
    script.load()
    print("[*] script loaded")

    if args.spawn:
        device.resume(pid)
        print("[*] resumed")

    print("[*] collecting for %ds, Ctrl+C to stop" % args.timeout)
    try:
        time.sleep(args.timeout)
    except KeyboardInterrupt:
        pass
    finally:
        f.close()
        try:
            session.detach()
        except Exception:
            pass
        print("[*] done, samples ->", OUT)


if __name__ == "__main__":
    main()

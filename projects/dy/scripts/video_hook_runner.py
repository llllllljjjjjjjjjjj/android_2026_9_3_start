# -*- coding: utf-8 -*-
# video_hook_runner.py — PID-attach 抖音专用 hook runner（绕开 frida 进程名本地化问题）
# 用法: python video_hook_runner.py <pid> <hook.js> [out.log]
import json
import os
import sys
import time

import frida

PID = int(sys.argv[1])
SCRIPT = sys.argv[2]
LOG = sys.argv[3] if len(sys.argv) > 3 else None

_fh = None
if LOG:
    _fh = open(LOG, "w", encoding="utf-8", errors="replace", buffering=1)


def emit(obj):
    line = json.dumps(obj, ensure_ascii=False, default=str)
    if _fh:
        _fh.write(line + "\n")
    else:
        print(line, flush=True)


def on_message(message, data):
    emit({"event": "message", "message": message,
          "data_hex": data.hex() if data else None})


def main():
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    device = frida.get_usb_device(timeout=10)
    session = device.attach(PID)
    source = open(SCRIPT, "r", encoding="utf-8").read()
    script = session.create_script(source)
    script.on("message", on_message)
    script.load()
    emit({"event": "ready", "pid": PID, "script": SCRIPT})
    while True:
        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        emit({"event": "error", "error": repr(exc)})
        sys.exit(1)

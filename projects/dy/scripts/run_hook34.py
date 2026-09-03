# -*- coding: utf-8 -*-
# run_hook34.py — 加载 dy_hook34_body_zstd.js，捕获搜索请求 body（含压缩态）
# 输出：capture/search_bodies/ 下的 base64 文件 + 自动尝试 zstd/gzip 解压并落盘
import base64
import gzip
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import frida

ADB = r"D:\reserve_agent\skills-portable-test\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
HOOK = r"D:\reserve_agent\skills-portable-test\projects\dy\hooks\dy_hook34_body_zstd.js"
OUTDIR = Path(r"D:\reserve_agent\skills-portable-test\projects\dy\capture\search_bodies")
OUTDIR.mkdir(exist_ok=True)

ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
GZIP_MAGIC = b"\x1f\x8b"

try:
    import zstandard as zstd
    zstd_ok = True
except ImportError:
    zstd_ok = False

saved = 0


def save_body(payload):
    global saved
    try:
        raw = base64.b64decode(payload["b64"])
    except Exception:
        return
    size = payload.get("size", len(raw))
    ts = int(time.time())
    name = f"body_{ts}_{size}b.bin"
    (OUTDIR / name).write_bytes(raw)
    saved += 1
    print(f"[SAVE] {name} raw={len(raw)}B saved={saved}", flush=True)

    # 尝试解压
    plain = None
    kind = ""
    if raw.startswith(ZSTD_MAGIC) and zstd_ok:
        try:
            plain = zstd.ZstdDecompressor().decompress(raw)
            kind = "zstd"
        except Exception:
            pass
    elif raw.startswith(GZIP_MAGIC):
        try:
            plain = gzip.decompress(raw)
            kind = "gzip"
        except Exception:
            pass
    if plain is not None:
        pname = name.replace(".bin", f".{kind}")
        (OUTDIR / pname).write_bytes(plain)
        kw = b""
        for probe in (b"meishi", b"keyword"):
            if probe in plain:
                kw = probe
                break
        print(f"[PLAIN] {pname} {kind} {len(plain)}B kw={'YES:' + kw.decode() if kw else 'no'}", flush=True)
        if kw:
            idx = plain.find(kw)
            print("[HEX@kw] " + plain[max(0, idx - 32):idx + 64].hex(), flush=True)


def on_message(msg, data):
    p = msg.get("payload")
    if isinstance(p, dict):
        t = p.get("t")
        if t == "sign":
            print(f"[SIGN] {p.get('ts')} {p.get('url', '')[:120]}", flush=True)
        elif t == "body":
            save_body(p)
        else:
            print(f"[MSG] {p}", flush=True)
    else:
        print(f"[RAW] {str(msg)[:200]}", flush=True)


def main():
    subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"])
    pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
    print("[*] attach pid =", pid, flush=True)
    dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
    s = dev.attach(pid)
    sc = s.create_script(open(HOOK, encoding="utf-8").read())
    sc.on("message", on_message)
    sc.load()
    print("[*] hook34 loaded, watching 180s（期间在真机触发搜索）...", flush=True)
    time.sleep(180)


if __name__ == "__main__":
    main()

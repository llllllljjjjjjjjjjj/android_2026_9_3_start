# -*- coding: utf-8 -*-
# run_hook35_34.py — 同会话双挂：hook35（证书 forge + QUIC 降级 + 搜索 dump）+
#                      hook34v2（body 双通道捕获）→ 触发搜索后抓真实 body
import base64
import gzip
import subprocess
import sys
import time
from pathlib import Path

import frida

ADB = r"D:\reserve_agent\skills-portable-test\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
HOOKS = [
    r"D:\reserve_agent\skills-portable-test\projects\dy\hooks\dy_hook35_combined.js",
    r"D:\reserve_agent\skills-portable-test\projects\dy\hooks\dy_hook34_body_zstd.js",
]
OUTDIR = Path(r"D:\reserve_agent\skills-portable-test\projects\dy\capture\search_bodies")
OUTDIR.mkdir(exist_ok=True)

ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
GZIP_MAGIC = b"\x1f\x8b"

try:
    import zstandard as zstd
    zstd_ok = True
except ImportError:
    zstd_ok = False

saved = {}


def save_body(payload):
    ch = payload.get("ch", "?")
    try:
        raw = base64.b64decode(payload["b64"])
    except Exception:
        return
    size = payload.get("size", len(raw))
    ts = int(time.time())
    n = saved.get(ch, 0) + 1
    saved[ch] = n
    name = f"ch{ch}_{ts}_{n}_{size}b.bin"
    (OUTDIR / name).write_bytes(raw)
    print(f"[SAVE] {name} ch={ch} raw={len(raw)}B", flush=True)

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
        kw = [w for w in (b"meishi", b"keyword", b"search") if w in plain]
        print(f"[PLAIN] {pname} {kind} {len(plain)}B kw={kw if kw else 'no'}", flush=True)
        for w in (b"meishi", b"keyword"):
            if w in plain:
                idx = plain.find(w)
                print("[HEX@kw] " + plain[max(0, idx - 48):idx + 96].hex(), flush=True)
                break


def on_message(msg, data):
    p = msg.get("payload")
    if isinstance(p, dict):
        t = p.get("t")
        if t == "body":
            save_body(p)
        elif t == "sign":
            print(f"[SIGN] {p.get('ts')} {p.get('url', '')[:120]}", flush=True)
        elif t == "info" or t == "ready":
            print(f"[INFO] {p.get('m', '')}", flush=True)
        else:
            print(f"[MSG] {p}", flush=True)
    else:
        txt = str(msg)[:160]
        if any(k in txt for k in ("[S]", "[SH]", "[forge]", "[quic]", "[cert]")):
            print(f"[D] {txt}", flush=True)


def main():
    subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"])
    pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
    print("[*] attach pid =", pid, flush=True)
    dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
    s = dev.attach(pid)
    for h in HOOKS:
        sc = s.create_script(open(h, encoding="utf-8").read())
        sc.on("message", on_message)
        sc.load()
        print(f"[*] loaded {Path(h).name}", flush=True)
        time.sleep(1)
    print("[*] 全部武装完成。请在真机触发搜索（或我发 deep link）。观察 240s...", flush=True)
    time.sleep(240)


if __name__ == "__main__":
    main()

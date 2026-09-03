# -*- coding: utf-8 -*-
# test_ecom_direct.py — PC 直发电商 GET 接口（oracle 签八神），验证是否 hit_shark
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import frida
import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
ROOT = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy")
HOOK21 = ROOT / "hooks" / "dy_hook21.js"
REQS = ROOT / "capture" / "detail_reqs.jsonl"
BAHSEN = ("x-argus", "x-gorgon", "x-helios", "x-khronos", "x-ladon", "x-medusa", "x-soter")


def hs_to_dict(hs):
    d = {}
    parts = hs.replace("\r\n", "\n").split("\n")
    for i in range(0, len(parts) - 1, 2):
        if parts[i].strip():
            d[parts[i].strip().lower()] = parts[i + 1]
    return d


def dict_to_hs(d):
    return "\r\n".join(f"{k}\r\n{v}" for k, v in d.items()) + "\r\n"


def refresh_url(url):
    sp = urlsplit(url)
    q = dict(parse_qsl(sp.query, keep_blank_values=True))
    q["_rticket"] = str(int(time.time() * 1000))
    q["ts"] = str(int(time.time()))
    return urlunsplit((sp.scheme, sp.netloc, sp.path, urlencode(q), sp.fragment))


def main():
    recs = [json.loads(l) for l in REQS.read_text(encoding="utf-8").splitlines() if l.strip()]
    # 选 preload（GET 无 body）
    rec = next(r for r in recs if "preload" in r["url"])
    url = refresh_url(rec["url"])
    hd = hs_to_dict(rec["headers"])
    for k in BAHSEN:
        hd.pop(k, None)

    # oracle 签八神
    subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"],
                          stdout=subprocess.DEVNULL)
    pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
    dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
    sess = dev.attach(pid)
    sc = sess.create_script(HOOK21.read_text(encoding="utf-8"))
    sc.load()
    time.sleep(1)
    out = sc.exports_sync.oracle(url, dict_to_hs(hd))
    sess.detach()
    sig = {}
    parts = out.replace("\r\n", "\n").split("\n")
    for i in range(0, len(parts) - 1, 2):
        k = parts[i].strip().lower()
        if k.startswith("x-"):
            sig[k] = parts[i + 1]
    print("八神签名 keys:", list(sig.keys()), flush=True)

    hd.update(sig)
    hd["accept-encoding"] = "gzip, deflate, br"
    print("PC 直发 preload (GET)...", flush=True)
    try:
        r = requests.get(url, headers=hd, timeout=15)
        print("status:", r.status_code, "len:", len(r.content), flush=True)
        raw = r.content
    except Exception as e:
        print("请求异常:", type(e).__name__, str(e)[:120], flush=True)
        return
    print("head:", raw[:200], flush=True)
    if b"hit_shark" in raw or b"antispam" in raw:
        print(">>> hit_shark！电商接口 PC 直发被网络指纹风控", flush=True)
    else:
        print(">>> 非 hit_shark，电商接口 PC 直发可行", flush=True)
    out = ROOT / "capture" / "preload_direct_resp.bin"
    out.write_bytes(raw)
    print("->", out)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
# detail_rpc.py — RPC oracle 调用抖音商品详情接口（detail/stream）
#
# 链路：
#   1) attach 抖音进程，挂 dy_hook21.js（八神 oracle）+ dy_hook38c.js（电商请求捕获）
#   2) App 打开商品详情页触发真实请求
#   3) RPC 拿 detail/stream 请求（URL + headers 串 + bodyB64）
#   4) 更新 URL 时间参数 → oracle 现场签名 → PC 直发 POST
#   5) 解析响应：产品参数 attr + 品牌资质 images.open_image → 下载图片
#
# 用法: python detail_rpc.py [--product-id 3770115268144136255] [--fresh]
import argparse
import base64
import json
import re
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
HOOK38C = ROOT / "hooks" / "dy_hook38c.js"
TMPL_FILE = ROOT / "capture" / "detail_stream_tmpl.json"

BAHSEN_KEYS = ("x-argus", "x-gorgon", "x-helios", "x-khronos", "x-ladon", "x-medusa", "x-soter")


def oracle_connect():
    subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"], stdout=subprocess.DEVNULL)
    pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
    dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
    sess = dev.attach(pid)
    scripts = {}
    for name, path in (("oracle", HOOK21), ("cap", HOOK38C)):
        scripts[name] = sess.create_script(path.read_text(encoding="utf-8"))
        scripts[name].load()
    time.sleep(1)
    return sess, scripts


def headers_str_to_dict(hs):
    """28065c 的 'name\\r\\nvalue\\r\\n...' 串 → dict"""
    d = {}
    parts = hs.replace("\r\n", "\n").split("\n")
    for i in range(0, len(parts) - 1, 2):
        k, v = parts[i].strip(), parts[i + 1] if i + 1 < len(parts) else ""
        if k:
            d[k.lower()] = v
    return d


def dict_to_headers_str(d):
    out = []
    for k, v in d.items():
        out.append(k)
        out.append(v)
    return "\r\n".join(out) + "\r\n"


def oracle_sign(sess_scripts, url, hs_str):
    out = sess_scripts["oracle"].exports_sync.oracle(url, hs_str)
    d = {}
    parts = out.replace("\r\n", "\n").split("\n")
    for i in range(0, len(parts) - 1, 2):
        k = parts[i].strip()
        if k:
            d[k.lower()] = parts[i + 1]
    return d


def refresh_url(url):
    now_s = int(time.time())
    now_ms = int(time.time() * 1000)
    sp = urlsplit(url)
    q = dict(parse_qsl(sp.query, keep_blank_values=True))
    q["_rticket"] = str(now_ms)
    q["ts"] = str(now_s)
    return urlunsplit((sp.scheme, sp.netloc, sp.path, urlencode(q), sp.fragment))


def post_detail(url, hdrs_dict, body, oracle_script):
    h = dict(hdrs_dict)
    for k in list(h):
        if k in BAHSEN_KEYS:
            del h[k]
    # 签名：headers 输入串（cookie 等基础头）
    hs_str = dict_to_headers_str({k: v for k, v in h.items()})
    sig = oracle_sign(None, url, hs_str) if False else None
    return h, hs_str


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fresh", action="store_true", help="重新抓请求模板（打开详情页触发）")
    args = ap.parse_args()

    sess, scripts = oracle_connect()
    print("oracle + capture hooked", flush=True)

    tmpl = None
    if not args.fresh and TMPL_FILE.exists():
        tmpl = json.loads(TMPL_FILE.read_text(encoding="utf-8"))
        print("loaded template:", tmpl.get("url", "")[:120], flush=True)

    if tmpl is None:
        # 打开详情页触发请求
        print("opening detail page...", flush=True)
        subprocess.check_call([ADB, "shell", "am", "start", "-a", "android.intent.action.VIEW",
                               "-d", "https://v.douyin.com/c11KamCtyGw/"], stdout=subprocess.DEVNULL)
        found = None
        for _ in range(30):
            try:
                recs = scripts["cap"].exports_sync.find("product/detail")
                for r in recs:
                    if "product/detail/stream" in r.get("url", "") and r.get("bodyB64"):
                        found = r
                        break
            except Exception:
                pass
            if found:
                break
            time.sleep(1)
        if not found:
            print("FAIL: stream request not captured", flush=True)
            return
        tmpl = {"url": found["url"], "headers": found["headers"], "bodyB64": found["bodyB64"]}
        TMPL_FILE.write_text(json.dumps(tmpl, ensure_ascii=False, indent=2), encoding="utf-8")
        print("template saved:", TMPL_FILE, flush=True)

    # 解析
    url = refresh_url(tmpl["url"])
    hdrs = headers_str_to_dict(tmpl["headers"])
    body = base64.b64decode(tmpl["bodyB64"])
    print("body size:", len(body), "head:", body[:16].hex(), flush=True)

    # 发送头调整：去 ttzip（服务器回普通压缩），去八神（oracle 重签）
    h = {k: v for k, v in hdrs.items() if k not in BAHSEN_KEYS}
    h["accept-encoding"] = "gzip, deflate, br"
    h.pop("ttzip-version", None)
    h.pop("x-bd-content-encoding", None)  # body 已是 zstd 压缩字节，头保留会双压缩！保留：服务器按头解压
    # 恢复（body 是 zstd，需要 x-bd-content-encoding: zstd）
    h["x-bd-content-encoding"] = "zstd"

    # oracle 签名输入串
    hs_str = dict_to_headers_str(h)
    print("oracle signing...", flush=True)
    sig = scripts["oracle"].exports_sync.oracle(url, hs_str)
    sigd = {}
    parts = sig.replace("\r\n", "\n").split("\n")
    for i in range(0, len(parts) - 1, 2):
        k = parts[i].strip()
        if k:
            sigd[k.lower()] = parts[i + 1]
    print("sig keys:", list(sigd.keys()), flush=True)
    if not any(k.startswith("x-") for k in sigd):
        print("WARN: signature looks empty/minimal:", sigd, flush=True)

    h.update(sigd)
    h["x-ss-req-ticket"] = str(int(time.time() * 1000))
    h["activity_now_client"] = str(int(time.time() * 1000))

    print("POST", url[:120], flush=True)
    r = requests.post(url, headers=h, data=body, timeout=30)
    print("status:", r.status_code, "len:", len(r.content), flush=True)
    raw = r.content
    # 响应：hex 前缀 + JSON 或直接 JSON
    s = raw.find(b"{")
    if s < 0:
        s = 0
    txt = raw[s:]
    try:
        data = json.loads(txt.decode("utf-8", errors="replace"))
    except Exception:
        print("response head:", raw[:400], flush=True)
        return
    out = ROOT / "capture" / "detail_stream_rpc_response.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print("response saved:", out, "top keys:", list(data.keys())[:10], flush=True)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
# detail_protocol.py — 电商详情接口协议化（oracle 重放模式，仿评论接口）
# 流程：attach oracle+capture → 短链打开详情页 → 抓 detail/stream 完整请求
#       → 解 body 找 product_id → 改 product_id + oracle 签八神 → PC 直发 → 解析响应
import argparse
import base64
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import frida
import requests
import zstandard as zstd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
ROOT = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy")
HOOK21 = ROOT / "hooks" / "dy_hook21.js"
HOOK38C = ROOT / "hooks" / "dy_hook38c.js"
TMPL = ROOT / "capture" / "detail_stream_tmpl.json"
BAHSEN = ("x-argus", "x-gorgon", "x-helios", "x-khronos", "x-ladon", "x-medusa", "x-soter")


def adb(*args):
    return subprocess.check_output([ADB, *args]).decode(errors="replace").strip()


def attach():
    subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"],
                          stdout=subprocess.DEVNULL)
    pid = int(adb("shell", "pidof", PKG).split()[0])
    dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
    sess = dev.attach(pid)
    oracle = sess.create_script(HOOK21.read_text(encoding="utf-8"))
    cap = sess.create_script(HOOK38C.read_text(encoding="utf-8"))
    oracle.load()
    cap.load()
    time.sleep(1)
    return sess, oracle, cap


def hs_to_dict(hs):
    d = {}
    parts = hs.replace("\r\n", "\n").split("\n")
    for i in range(0, len(parts) - 1, 2):
        if parts[i].strip():
            d[parts[i].strip().lower()] = parts[i + 1]
    return d


def dict_to_hs(d):
    return "\r\n".join(f"{k}\r\n{v}" for k, v in d.items()) + "\r\n"


def sign(oracle, url, hd):
    out = oracle.exports_sync.oracle(url, dict_to_hs(hd))
    sig = {}
    parts = out.replace("\r\n", "\n").split("\n")
    for i in range(0, len(parts) - 1, 2):
        k = parts[i].strip().lower()
        if k.startswith("x-"):
            sig[k] = parts[i + 1]
    return sig


def refresh_url(url):
    sp = urlsplit(url)
    q = dict(parse_qsl(sp.query, keep_blank_values=True))
    q["_rticket"] = str(int(time.time() * 1000))
    q["ts"] = str(int(time.time()))
    return urlunsplit((sp.scheme, sp.netloc, sp.path, urlencode(q), sp.fragment))


def open_detail(code):
    subprocess.check_call([ADB, "shell", "am", "start", "-a",
                           "android.intent.action.VIEW", "-d", f"https://v.douyin.com/{code}/"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def capture_stream(cap, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            for r in cap.exports_sync.find("product/detail"):
                if "product/detail/stream" in r.get("url", "") and r.get("bodyB64"):
                    return r
        except Exception:
            pass
        time.sleep(1)
    return None


def post_detail(url, hd, body):
    h = dict(hd)
    for k in BAHSEN:
        h.pop(k, None)
    h["accept-encoding"] = "gzip, deflate, br"
    h["x-bd-content-encoding"] = "zstd"
    r = requests.post(url, headers=h, data=body, timeout=30)
    return r


def parse_resp(raw):
    s = raw.find(b"{")
    txt = raw[s:] if s >= 0 else raw
    return json.loads(txt.decode("utf-8", errors="replace"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default="c11KamCtyGw", help="短链 code（默认溪木源）")
    ap.add_argument("--product-id", default="", help="覆盖 product_id（协议化换商品）")
    ap.add_argument("--fresh", action="store_true", help="重新抓模板")
    args = ap.parse_args()

    sess, oracle, cap = attach()
    print("oracle + capture 已挂载", flush=True)

    tmpl = None
    if not args.fresh and TMPL.exists():
        tmpl = json.loads(TMPL.read_text(encoding="utf-8"))
        print("加载已有模板", flush=True)
    if tmpl is None:
        print("打开详情页抓请求...", flush=True)
        open_detail(args.code)
        rec = capture_stream(cap)
        if not rec:
            print("FAIL: 未捕获 detail/stream 请求", flush=True)
            sess.detach()
            sys.exit(1)
        tmpl = {"url": rec["url"], "headers": rec["headers"], "bodyB64": rec["bodyB64"]}
        TMPL.write_text(json.dumps(tmpl, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"模板已保存 body={len(tmpl['bodyB64'])//3*2}B", flush=True)

    url = refresh_url(tmpl["url"])
    hd = hs_to_dict(tmpl["headers"])
    body = base64.b64decode(tmpl["bodyB64"])

    # 解 body 找 product_id（zstd 压缩表单）
    plain = zstd.ZstdDecompressor().decompressobj().decompress(body)
    form = dict(parse_qsl(plain.decode("utf-8", errors="replace"), keep_blank_values=True))
    print("body 明文字段:", list(form.keys())[:15], flush=True)
    pid_key = next((k for k in form if "product_id" in k.lower()), None)
    print("product_id 字段:", pid_key, "=", form.get(pid_key), flush=True)

    if args.product_id and pid_key:
        form[pid_key] = args.product_id
        body = zstd.ZstdCompressor(level=3).compress(urlencode(form).encode())
        print(f"已替换 product_id -> {args.product_id}", flush=True)

    sig = sign(oracle, url, hd)
    print("八神签名:", {k: v[:20] for k, v in sig.items()}, flush=True)
    hd.update(sig)
    hd["x-ss-req-ticket"] = str(int(time.time() * 1000))

    print("PC 直发...", flush=True)
    r = post_detail(url, hd, body)
    print("status:", r.status_code, "len:", len(r.content), flush=True)

    raw = r.content
    if b"hit_shark" in raw or b"antispam" in raw:
        print(">>> 命中 hit_shark：电商接口 PC 直发被网络指纹风控", flush=True)
        sess.detach()
        sys.exit(2)
    data = parse_resp(raw)
    out = ROOT / "capture" / "detail_protocol_resp.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"响应已保存 {out}，top keys: {list(data.keys())[:8]}", flush=True)
    sess.detach()


if __name__ == "__main__":
    main()

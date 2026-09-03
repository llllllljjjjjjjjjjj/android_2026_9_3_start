# -*- coding: utf-8 -*-
# replay_search.py — 原样重放 Charles 抓到的真实搜索请求（默认 session5 entry74 新身份），
#                    只重新生成八神签名；--session/--entry 可换
# 目的：区分 hit_shark 是「IP/设备级风控」还是「缺设备参数」导致
import argparse
import base64
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import frida
import requests
import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
ADB = r"D:\reserve_agent\skills-portable-test\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
HOOK = ROOT / "hooks" / "dy_hook21.js"
SESSION = ROOT / "capture" / "charles_session5.json"
ENTRY = 74

_orig_gai = socket.getaddrinfo


def _gai_v4(host, *a, **k):
    return [x for x in _orig_gai(host, *a, **k) if x[0] == socket.AF_INET] or _orig_gai(host, *a, **k)


socket.getaddrinfo = _gai_v4

_script = None
COOKIE = ""
UA = ""


def oracle_connect():
    global _script
    subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"])
    pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
    dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
    _script = dev.attach(pid).create_script(open(HOOK, encoding="utf-8").read())
    _script.load()
    time.sleep(2)


def oracle_sign(url, stub):
    global _script
    if _script is None:
        oracle_connect()
    base_hdr = ("cookie\r\n" + COOKIE + "\r\nuser-agent\r\n" + UA + "\r\naccept-encoding\r\ngzip, deflate, br")
    out = _script.exports_sync.oracle(url, base_hdr + "\r\nx-ss-stub\r\n" + stub)
    parts = out.split("\r\n")
    return {parts[i]: parts[i + 1] for i in range(0, len(parts) - 1, 2)}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", default=str(SESSION))
    ap.add_argument("--entry", type=int, default=globals().get("ENTRY", 74))
    ap.add_argument("--latest", action="store_true", help="自动选会话中最新 general/stream POST COMPLETE 条目")
    ap.add_argument("--proxy", default=None, help="走代理转发（如 http://127.0.0.1:8888 与 App 同上下文）")
    args = ap.parse_args()

    session = Path(args.session) if args.session != str(SESSION) else SESSION
    d = json.loads(session.read_text(encoding="utf-8-sig"))
    if args.latest:
        cand = [i for i, e in enumerate(d)
                if e.get("method") == "POST" and "general/stream" in (e.get("path") or "")
                and e.get("status") == "COMPLETE" and (e.get("request") or {}).get("body")]
        if not cand:
            print("no latest general/stream COMPLETE with body found")
            return
        ENTRY = cand[-1]
        print(f"[*] latest entry = {ENTRY}")
    else:
        ENTRY = args.entry
    e = d[ENTRY]
    req = e["request"]
    hdrs = {}
    COOKIE = ""
    UA = ""
    for h in req["header"]["headers"]:
        n = h.get("name", "")
        v = h.get("value", "")
        if n.startswith(":"):
            continue
        ln = n.lower()
        if ln == "cookie":
            COOKIE += v + "; " if not COOKIE else v + "; "
        elif ln == "user-agent":
            UA = v
        elif ln in ("x-argus", "x-gorgon", "x-helios", "x-khronos", "x-ladon", "x-medusa"):
            continue
        else:
            hdrs[n] = v
    COOKIE = COOKIE.rstrip("; ")
    global COOKIE_G, UA_G
    COOKIE_G, UA_G = COOKIE, UA
    globals()["COOKIE"] = COOKIE
    globals()["UA"] = UA
    url = f"https://{e['host']}{e['path']}?{e.get('query') or ''}"
    body = base64.b64decode(req["body"]["encoded"])
    plain = zstd.ZstdDecompressor().decompressobj().decompress(body)
    print("[*] body raw=%dB decompressed=%dB" % (len(body), len(plain)))
    stub = hdrs.get("x-ss-stub", "0123456789abcdef0123456789abcdef")
    hdrs.pop("content-length", None)
    hdrs.pop("x-ss-req-ticket", None)
    # 保留 x-bd-content-encoding=zstd（服务器靠它解 body）；响应用 template_dict 解
    hdrs["accept-encoding"] = "gzip, deflate"
    hdrs.update(oracle_sign(url, stub))
    hdrs["x-ss-req-ticket"] = str(int(time.time() * 1000))
    s = requests.Session()
    s.trust_env = False
    if args.proxy:
        s.proxies = {"http": args.proxy, "https": args.proxy}
        s.verify = False
    r = s.post(url, headers=hdrs, data=body, timeout=30)
    raw = r.content
    if raw[:4] == b"\x28\xb5\x2f\xfd":
        # 服务器用预训练字典压缩（assets/template_dict_v1.zstdict，已从 APK 提取）
        ddict = zstd.ZstdCompressionDict((ROOT / "capture" / "search_bodies" / "template_dict_v1.zstdict").read_bytes())
        raw = zstd.ZstdDecompressor(dict_data=ddict).decompressobj().decompress(raw)
    elif r.headers.get("content-encoding") == "gzip" and raw[:2] == b"\x1f\x8b":
        import gzip as _gzip
        raw = _gzip.decompress(raw)
    print("[*] http", r.status_code, "body head:", raw[:40].hex())
    si = raw.find(b"{")
    if si > 0:
        raw = raw[si:]
    j = json.JSONDecoder().raw_decode(raw.decode("utf-8", errors="replace"))[0]
    (ROOT / "capture" / "replay_response.json").write_text(json.dumps(j, ensure_ascii=False), encoding="utf-8")
    print("[*] response saved to capture/replay_response.json")
    print("status_code =", j.get("status_code"))
    lp = j.get("log_pb") or {}
    nil = (lp.get("stab_extra") or {}).get("NilInfoContext") or {}
    print("nil:", nil.get("search_nil_type"), "/", nil.get("search_nil_item"))
    print("top keys:", list(j.keys())[:10])
    st = j.get("struct")
    print("struct:", (list(st.keys())[:6] if isinstance(st, dict) else st))
    out = []

    def walk(o, dep=0):
        if dep > 7:
            return
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("aweme_info", "aweme_list") and isinstance(v, list):
                    out.extend(v)
                else:
                    walk(v, dep + 1)
        elif isinstance(o, list):
            for x in o:
                walk(x, dep + 1)
    walk(j)
    print("aweme entries:", len(out))
    for a in out[:6]:
        ai = a.get("aweme_info") or a
        if isinstance(ai, dict):
            print("   -", (ai.get("desc") or "")[:48], "|", (ai.get("author") or {}).get("nickname", ""),
                  "|", ai.get("aweme_id"))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""验证 mtgsig 的 a2 字段是否 = MD5(baseString)（纯算验证）

复现 MainBridge.main2 case75 + sign/core/gmtkby.java 的 baseString 构造：
  1. path = URL 的 path
  2. query 参数 decode -> encode(Uri.encode(s, "-._~") + 特殊表) -> 按 (key,value) 排序 -> k=v&k=v&...
  3. baseString = METHOD + " " + path + " " + params
  4. 无 body: input = baseString bytes; 有 body: input = baseString bytes + body[:16200]
  5. a2 = MD5(input) ?
"""
import hashlib
import json
import re
import sys
import urllib.parse

# ---- 从采集样本提取 (url, mtgsig) ----
SAMPLE = r"D:\reserve_agent\ish-portable-kit\projects\dianping\capture\mtgsig_samples.jsonl"


def load_review_sample():
    with open(SAMPLE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if obj.get("type") != "babelV4":
                continue
            url = obj.get("url", "")
            sig = obj.get("mtgsig")
            if "reviewlist" in url and sig:
                return url, json.loads(sig) if isinstance(sig, str) else sig
    return None, None


# Android Uri.encode(s, "-._~") 复现
_UNRESERVED = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
# zqffimcx 特殊表（Uri.encode 后补充转义）
_EXTRA = {ord("!"): "%21", ord("'"): "%27", ord("("): "%28", ord(")"): "%29", ord("*"): "%2A"}


def android_uri_encode(s):
    out = []
    for ch in s:
        o = ord(ch)
        if ch in _UNRESERVED:
            out.append(ch)
        elif o in _EXTRA:
            out.append(_EXTRA[o])
        else:
            b = ch.encode("utf-8")
            out.append("".join("%%%02X" % x for x in b))
    return "".join(out)


def build_params(encoded_query):
    """从 encodedQuery 拆分 -> decode -> encode -> 排序 -> k=v&k=v&..."""
    entries = []
    if not encoded_query:
        return ""
    for pair in encoded_query.split("&"):
        if not pair:
            continue
        if "=" in pair:
            k, v = pair.split("=", 1)
        else:
            k, v = pair, ""
        # Uri.decode 复现 (percent decode)
        kd = urllib.parse.unquote(k)
        vd = urllib.parse.unquote(v)
        entries.append((kd, vd))
    # encode
    enc = [(android_uri_encode(k), android_uri_encode(v)) for (k, v) in entries]
    # 先按 value 排序，再按 key 排序（稳定排序 => (key, value) 字典序）
    enc.sort(key=lambda e: e[1])
    enc.sort(key=lambda e: e[0])
    return "&".join("%s=%s" % (k, v) for (k, v) in enc)


def build_base_string(method, url, body=b""):
    parsed = urllib.parse.urlsplit(url)
    path = parsed.path or "/"
    if not path:
        path = "/"
    params = build_params(parsed.query)
    base = "%s %s %s" % (method.upper(), path, params)
    data = base.encode("utf-8")
    if body:
        data = data + body[:16200]
    return base, data


def md5_hex(b):
    return hashlib.md5(b).hexdigest()


def main():
    url, sig = load_review_sample()
    if not url or not sig:
        print("[-] no reviewlist sample with mtgsig found")
        sys.exit(1)

    print("[+] URL:", url[:160], "...")
    print("[+] a2 target:", sig.get("a2"))
    print("[+] a0:", sig.get("a0"), " a1:", sig.get("a1"))

    base, data = build_base_string("GET", url)
    print("[+] baseString:", base[:200], "...")
    print("[+] input bytes:", len(data))

    cand = md5_hex(data)
    print("[+] MD5(input) =", cand)
    print("[+] match:", cand == sig.get("a2"))

    # 也试几个变体
    variants = {
        "md5(base)": md5_hex(base.encode()),
        "md5(md5(input))": md5_hex(md5_hex(data).encode()),
        "md5(base+host)": md5_hex((base + "mapi.dianping.com").encode()),
    }
    for name, v in variants.items():
        if v == sig.get("a2"):
            print("[+] VARIANT MATCH:", name, v)
    print("[+] done")


if __name__ == "__main__":
    main()

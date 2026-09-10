# -*- coding: utf-8 -*-
"""dy 搜索接口 POC：用抓到的真实 body + 头，实测能否打通（单次，遵守验证纪律）
数据来源：
  body  -> capture/body_full.txt (@@@BODY_BEGIN..@@@BODY_END)
  token -> capture/headermap.txt (X-Tt-Token / x-bd-client-key 实样)
"""
import re, json, sys, os
import urllib.request

BASE = r"D:\reserve_agent\android\projects\dy"
BODY_FILE = os.path.join(BASE, "capture", "body_full.txt")
HM_FILE = os.path.join(BASE, "capture", "headermap.txt")

URL = "https://search3-search.amemv.com/aweme/v2/search/general/stream/"


def read_text(path):
    """PowerShell Tee-Object 默认写 UTF-16LE -> 自适应解码"""
    raw = open(path, "rb").read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", errors="ignore")
    if raw[:3] == b"\xef\xbb\xbf":
        return raw.decode("utf-8-sig", errors="ignore")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-16", errors="ignore")


def extract_body():
    """按行解析取 general/stream 的完整 body（避免正则前缀问题）"""
    lines = read_text(BODY_FILE).splitlines()
    idx = None
    for i, l in enumerate(lines):
        if "@@@REQ" in l and "/aweme/v2/search/general/stream/" in l:
            idx = i
            break
    if idx is None:
        return None
    for j in range(idx, min(idx + 12, len(lines))):
        if lines[j].strip() == "@@@BODY_BEGIN":
            k = j + 1
            buf = []
            while k < len(lines) and lines[k].strip() != "@@@BODY_END":
                buf.append(lines[k])
                k += 1
            return "\n".join(buf)
    return None


def extract_token():
    """字符串定位取值（避免正则/前缀问题）"""
    txt = read_text(HM_FILE)
    out = {}
    key = '"X-Tt-Token":"'
    i = txt.find(key)
    if i >= 0:
        s = i + len(key)
        out["X-Tt-Token"] = txt[s:txt.find('"', s)]
    key2 = '"x-bd-client-key":["'
    i2 = txt.find(key2)
    if i2 >= 0:
        s2 = i2 + len(key2)
        out["x-bd-client-key"] = txt[s2:txt.find('"', s2)]
    return out


def main():
    body = extract_body()
    toks = extract_token()
    print("[*] body len:", len(body) if body else None)
    print("[*] tokens:", {k: v[:40] + "..." for k, v in toks.items()})
    if not body:
        print("[!] body not found"); return

    headers = {
        "Host": "aweme.snssdk.com",
        "User-Agent": "com.ss.android.ugc.aweme/380001 (Linux; U; Android 10; zh_CN_#Hans; Pixel 4; Build/QQ3A.200605.001; Cronet/TTNetVersion:0fa322de 2024-11-06)",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept-Encoding": "gzip, deflate",
        "X-Tt-Token": toks.get("X-Tt-Token", ""),
        "x-bd-client-key": toks.get("x-bd-client-key", ""),
        "x-bd-kmsv": "1",
        "x-tt-ext-info": "etag=0;net_type=2;version=4.2.243.28-douyin",
    }

    req = urllib.request.Request(URL, data=body.encode("utf-8"), headers=headers, method="POST")
    print("[*] sending single request (validation discipline: single attempt)...")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = resp.read()
            print("[*] HTTP", resp.status, "len=", len(data))
            print("[*] body head:", data[:600].decode("utf-8", "ignore"))
            with open(os.path.join(BASE, "capture", "poc_response.txt"), "wb") as f:
                f.write(data)
    except Exception as e:
        print("[!] request failed:", type(e).__name__, e)
        try:
            print("[!] resp body:", e.read()[:400].decode("utf-8", "ignore"))
        except Exception:
            pass


if __name__ == "__main__":
    main()

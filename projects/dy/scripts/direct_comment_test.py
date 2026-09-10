# -*- coding: utf-8 -*-
"""路径 2 验证：用抓到的完整签名头 + Cookie 重发评论请求
数据来源: capture/signature_headers.json（native 层 HPACK 解出的真实头）
判官: 响应是否含真实评论（"cid"），或是否仍为 -99999
"""
import json, os, time, gzip, urllib.request, urllib.error
from urllib.parse import urlparse, parse_qsl, urlencode

D = r"D:\reserve_agent\android\projects\dy\capture"
SIG = os.path.join(D, "signature_headers.json")
REQ = os.path.join(D, "comment_request_capture.json")
OUT = os.path.join(D, "direct_comment_response.txt")


def load_sig():
    """把 HPACK 解出的 header 组转成 python dict"""
    j = json.load(open(SIG, encoding="utf-8"))
    hdrs = {}
    cookies = []
    pseudo = {}
    for n, v in j["headers"]:
        if n.startswith(":"):
            pseudo[n] = v
        elif n.lower() == "cookie":
            cookies.append(str(v))
        else:
            hdrs[n] = str(v)
    if cookies:
        # 多条 cookie 合并为一条
        merged = []
        for c in cookies:
            merged.append(c)
        hdrs["Cookie"] = "; ".join(merged)
    return pseudo, hdrs


def main():
    pseudo, hdrs = load_sig()
    print(f"[*] 签名头 {len(hdrs)} 项，其中 Cookie 项 {len(hdrs.get('Cookie','').split(';'))} 个")
    print(f"[*] authority={pseudo.get(':authority')}")

    r = json.load(open(REQ, encoding="utf-8"))
    url = r["url"]
    print(f"[*] 原始评论 URL len={len(url)}")
    q = dict(parse_qsl(urlparse(url).query))
    print(f"[*] 参数 {len(q)} 个；aweme_id={q.get('aweme_id')} cursor={q.get('cursor')}")

    # 换 host 为抓到头的 authority？先保持原 host，只换 header
    body = (r.get("body") or "").encode("utf-8")
    print(f"[*] body len={len(body)}")

    # 组装请求头（去掉 HTTP/2 伪头）
    send = dict(hdrs)
    send.setdefault("User-Agent", "com.ss.android.ugc.aweme/380001")
    send["Content-Type"] = "application/x-www-form-urlencoded"
    send.pop("content-length", None)   # 让 urllib 自己算

    print(f"[*] 发送 header 列表: {sorted(send.keys())}")
    req = urllib.request.Request(url, data=body if body else None,
                                 headers=send, method=r.get("method") or "POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            if raw[:2] == b"\x1f\x8b" or "gzip" in (resp.headers.get("Content-Encoding") or ""):
                raw = gzip.decompress(raw)
            txt = raw.decode("utf-8", "ignore")
            print(f"\n[*] HTTP {resp.status} len={len(txt)}")
            print(f"[*] head: {txt[:400]}")
            ok = '"cid"' in txt
            bad = "-99999" in txt
            print(f"\n[*] ★ 含真实评论: {ok}   |   风控码 -99999: {bad}")
            if ok:
                print("[*] ★★★ 协议直发成功 ★★★")
            open(OUT, "w", encoding="utf-8").write(txt)
            print(f"[*] 已保存 -> {OUT}")
    except urllib.error.HTTPError as e:
        print(f"[!] HTTP {e.code}")
        try:
            print("[!] body:", e.read()[:500].decode("utf-8", "ignore"))
        except Exception:
            pass
    except Exception as e:
        print(f"[!] 失败: {type(e).__name__} {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

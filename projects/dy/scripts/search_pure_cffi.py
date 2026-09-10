# -*- coding: utf-8 -*-
"""TLS 指纹模拟直发: curl_cffi(impersonate=chrome131_android) 传输 + search_pure 纯算构造
对照实验: 仅传输层 TLS 指纹从 Python/OpenSSL 换成 BoringSSL/Chrome-Android
"""
import sys, time, json, urllib.parse
sys.path.insert(0, r"D:\reserve_agent\android\projects\dy\scripts")
import search_pure as sp
from curl_cffi import requests as cr

KW = sys.argv[1] if len(sys.argv) > 1 else "太阳"
IMPERSONATE = sys.argv[2] if len(sys.argv) > 2 else "chrome131_android"


def main():
    samples = sp.load_header_samples()
    sample = samples[0]
    query_sample = sp.pick_query_sample(samples)
    bodies = sp.extract_bodies()
    tmpl = bodies[sp.SEARCH_PATH]
    tpl_params = dict(urllib.parse.parse_qsl(tmpl, keep_blank_values=True))
    keep = len(tpl_params.get("search_rerank_info", "")) > 100

    now_s, now_ms = int(time.time()), int(time.time() * 1000)
    prev_ts = now_ms - 60000

    # 前置
    if sp.HISTORY_PATH in bodies:
        url1 = f"https://{sp.HISTORY_HOST}{sp.HISTORY_PATH}?{sp.build_public_query(query_sample, now_s, now_ms)}"
        hb = sp.build_history_body(bodies[sp.HISTORY_PATH], KW, now_ms)
        h1 = sp.build_headers(sample, now_s, now_ms, sp.HISTORY_HOST, sp.compute_stub(hb.encode()))
        try:
            r1 = cr.post(url1, data=hb.encode(), headers=h1, impersonate=IMPERSONATE, timeout=20)
            print(f"[*] 前置 history -> HTTP {r1.status_code} ({len(r1.content)}B)")
        except Exception as e:
            print("[!] 前置:", type(e).__name__, str(e)[:100])

    # 主请求
    body = sp.build_search_body(tmpl, KW, 10, 0, prev_ts, None, keep)
    stub = sp.compute_stub(body.encode())
    hdrs = sp.build_headers(sample, now_s, now_ms, sp.SEARCH_HOST, stub)
    url = f"https://{sp.SEARCH_HOST}{sp.SEARCH_PATH}?{sp.build_public_query(query_sample, now_s, now_ms)}"
    print(f"[*] POST via curl_cffi impersonate={IMPERSONATE} | body {len(body)}B")

    r = cr.post(url, data=body.encode(), headers=hdrs, impersonate=IMPERSONATE, timeout=30)
    print(f"[*] HTTP {r.status_code} | len={len(r.content)} | CE={r.headers.get('content-encoding')}")
    raw = r.content
    open(r"D:\reserve_agent\android\projects\dy\capture\_cffi_raw.bin", "wb").write(raw)

    ok, verdict, texts, data = sp.parse_response(raw)
    print("[*] 判官:", verdict)
    items = sp.extract_items(data) if data else []
    print("[*] 条目:", len(items))
    for t in texts[:2]:
        print("[*] 响应块:", t[:220])
    if items:
        for it in items[:5]:
            print("    aid=%s desc=%s" % (it.get("aweme_id"), str(it.get("desc"))[:50]))
    json.dump({"kw": KW, "impersonate": IMPERSONATE, "verdict": verdict, "ok": ok,
               "items": items, "raw_head": raw[:500].decode("utf-8", "ignore")},
              open(r"D:\reserve_agent\android\projects\dy\capture\pure_cffi_result.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return 0 if (ok and items) else 3


if __name__ == "__main__":
    sys.exit(main())

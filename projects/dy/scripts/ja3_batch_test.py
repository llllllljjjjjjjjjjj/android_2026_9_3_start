# -*- coding: utf-8 -*-
"""批量测试各 TLS 指纹对 hit_shark 的影响（同一构造，仅换 impersonate）"""
import sys, time, urllib.parse
sys.path.insert(0, r"D:\reserve_agent\android\projects\dy\scripts")
import search_pure as sp
from curl_cffi import requests as cr

KW = "太阳"
TARGETS = ["chrome110", "chrome116", "chrome120", "chrome124", "chrome131", "chrome133a"]

samples = sp.load_header_samples()
sample = samples[0]
qs = sp.pick_query_sample(samples)
bodies = sp.extract_bodies()
tmpl = bodies[sp.SEARCH_PATH]
tplp = dict(urllib.parse.parse_qsl(tmpl, keep_blank_values=True))
keep = len(tplp.get("search_rerank_info", "")) > 100

for imp in TARGETS:
    now_s, now_ms = int(time.time()), int(time.time() * 1000)
    body = sp.build_search_body(tmpl, KW, 10, 0, now_ms - 60000, None, keep)
    hdrs = sp.build_headers(sample, now_s, now_ms, sp.SEARCH_HOST, sp.compute_stub(body.encode()))
    url = f"https://{sp.SEARCH_HOST}{sp.SEARCH_PATH}?{sp.build_public_query(qs, now_s, now_ms)}"
    try:
        r = cr.post(url, data=body.encode(), headers=hdrs, impersonate=imp, timeout=25)
        ok, verdict, texts, data = sp.parse_response(r.content)
        items = sp.extract_items(data) if data else []
        print(f"{imp:14s} HTTP {r.status_code} {len(r.content):6d}B verdict={verdict} items={len(items)}")
    except Exception as e:
        print(f"{imp:14s} ERR {type(e).__name__}: {str(e)[:80]}")
    time.sleep(2)

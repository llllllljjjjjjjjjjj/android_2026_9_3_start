# -*- coding: utf-8 -*-
"""分析 POC 重放的 body 关键参数（时间戳/search_id 等），判断空结果原因"""
import sys
sys.path.insert(0, r"D:\reserve_agent\android\projects\dy\scripts")
from poc_search import extract_body, read_text, BODY_FILE
import urllib.parse, re, time

body = extract_body()
print("body len:", len(body))
pairs = urllib.parse.parse_qsl(body, keep_blank_values=True)
print("param count:", len(pairs))
print("\n--- all keys ---")
for i, (k, v) in enumerate(pairs):
    vs = v if len(v) < 90 else v[:90] + "..."
    print(f"{i:3d} {k} = {vs}")

print("\n--- suspicious(timestamp/id/sign) ---")
for k, v in pairs:
    if re.search(r"time|ts$|id$|sign|token|nonce|search", k, re.I):
        vs = v if len(v) < 120 else v[:120] + "..."
        print(f"  {k} = {vs}")

print("\nnow ms:", int(time.time() * 1000))

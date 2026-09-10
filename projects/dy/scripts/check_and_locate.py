# -*- coding: utf-8 -*-
"""检查 1) 抓到的流内容特征 2) 定位 v2 搜索响应模型"""
import re, os, glob

P = r"D:\reserve_agent\android\projects\dy\capture\resp_stream.bin"
if os.path.exists(P):
    raw = open(P, "rb").read()
    print("stream size:", len(raw))
    print("sample:", raw[:160])
    for kw in [b"HTTP/", b"aweme", b"search", b"content-encoding", b"gzip", b"\x1f\x8b"]:
        print(f"  {kw}: {raw.count(kw)}")
    pr = sum(1 for b in raw[:200000] if 32 <= b < 127 or b in (9, 10, 13))
    print("printable ratio (first 200KB): %.3f" % (pr / 200000))

print("\n--- v2 search general package models ---")
base = r"D:\reserve_agent\android\projects\dy\decompiled\sources\com\ss\ugc\android\ugc\aweme\search\general"
if os.path.isdir(base):
    fs = glob.glob(os.path.join(base, "**", "*"), recursive=True)
    files = [f for f in fs if f.endswith(".java")]
    print("file count:", len(files))
    for f in files[:25]:
        print("  ", os.path.relpath(f, base))
else:
    print("dir not found:", base)

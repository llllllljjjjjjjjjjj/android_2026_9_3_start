# -*- coding: utf-8 -*-
# analyze_qual_context.py — 在 memscan 片段中定位 qualification 相关字段与图片 URL 上下文
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "capture" / "memscan_json"

KEYS = ["qualif", "brand", "certif", "license", "author", "spec", "parameter", "prod_qual", "qual_im"]

for f in sorted(D.glob("json_*.txt")):
    raw = f.read_text(encoding="utf-8", errors="replace")
    urls = re.findall(r"https?:\\?/\\?/[^\"'\s\\]{10,600}?\.(?:png|jpg|jpeg|webp|heic|gif)[^\"'\s\\]*", raw)
    urls = [u.replace("\\/", "/") for u in urls]
    qual_urls = []
    for u in urls:
        pos = raw.find(u.replace("/", "\\/"))
        if pos < 0:
            pos = raw.find(u)
        ctx = raw[max(0, pos - 400):pos]
        if any(k in ctx.lower() for k in ["qualif", "brand", "certif", "license", "author", "spec"]):
            qual_urls.append(u)
    if qual_urls:
        print(f"== {f.name}: {len(qual_urls)} qual-context urls ==")
        for u in dict.fromkeys(qual_urls):
            print("   ", u[:220])

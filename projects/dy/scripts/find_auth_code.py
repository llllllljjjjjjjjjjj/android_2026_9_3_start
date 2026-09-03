# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\decompiled\sources\com\bytedance\android\shopping")

KWS = ["官方授权", "授权书", "资质详情", "品牌授权", "authorization", "Authorization"]
hits = []
for f in ROOT.rglob("*.java"):
    try:
        txt = f.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    for kw in KWS:
        i = txt.find(kw)
        if i >= 0:
            line_no = txt[:i].count("\n") + 1
            hits.append((kw, f, line_no))
            break

for kw, f, ln in hits:
    print(f"{kw} -> {f}:{ln}")

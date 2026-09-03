# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\decompiled\sources\com\bytedance\android\shopping\anchorv4")

KWS = ["官方授权", "授权", "资质", "qualification", "Qualification", "authorization", "Authorization", "license", "License"]
seen = set()
for f in ROOT.rglob("*.java"):
    try:
        txt = f.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    for kw in KWS:
        i = txt.find(kw)
        if i >= 0 and f not in seen:
            seen.add(f)
            line_no = txt[:i].count("\n") + 1
            print(f"{kw} -> {f}:{line_no}")
            break

print("total files scanned:", len(list(ROOT.rglob("*.java"))))

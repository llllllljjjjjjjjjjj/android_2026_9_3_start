# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\decompiled\sources\com\bytedance\android")

KWS = ["property_name_all", "propertyNameAll", "attr_name", "适用人群", "official_auth", "officialAuth",
       "brand_official", "authDialog", "AuthorizationDialog", "open_image", "openImage"]
seen = set()
for f in ROOT.rglob("*.java"):
    try:
        txt = f.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    for kw in KWS:
        i = txt.find(kw)
        if i >= 0 and str(f) not in seen:
            seen.add(str(f))
            line_no = txt[:i].count("\n") + 1
            print(f"{kw} -> {f}:{line_no}")
            break

print("done")

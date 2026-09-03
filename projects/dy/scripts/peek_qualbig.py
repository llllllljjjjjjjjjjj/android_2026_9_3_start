# -*- coding: utf-8 -*-
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
D = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\qualbig")
for f in sorted(D.glob("qual_*.json")):
    raw = f.read_text(encoding="utf-8", errors="replace")
    for kw in ["qualification", "资质", "multipleLicenses", "cert"]:
        idx = raw.find(kw)
        if idx < 0:
            continue
        ctx = raw[max(0, idx - 150):idx + 250].replace("\\\\", "\\")
        print(f"== {f.name} [{kw}] ==")
        print(ctx[:400])
        print()
        break

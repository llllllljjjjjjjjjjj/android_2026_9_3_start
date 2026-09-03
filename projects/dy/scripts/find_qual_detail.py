# -*- coding: utf-8 -*-
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
D = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\memscan_json")
for f in sorted(D.glob("json_*.txt")):
    raw = f.read_text(encoding="utf-8", errors="replace")
    for kw in ["资质", "qualification_detail", "qualification_list", "brand_qualification", "qualification_url",
               "certificate", "cert_url", "authorization"]:
        idx = raw.find(kw)
        if idx >= 0:
            print(f"== {f.name} [{kw}] @{idx} ==")
            print(raw[max(0, idx - 200):idx + 600].replace("\\\\", "\\"))
            print()

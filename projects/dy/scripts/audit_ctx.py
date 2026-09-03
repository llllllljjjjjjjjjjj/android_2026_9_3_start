# -*- coding: utf-8 -*-
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
s = open(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\detail_ctx.json", encoding="utf-8", errors="replace").read()
i = s.find("property_name_all")
tail = s[i:]
for kw in ["audit_status", "image_addr", "cover_id"]:
    hits = [m.start() for m in re.finditer(kw, tail)]
    print(f"== {kw} x{len(hits)} ==")
    for h in hits[:2]:
        print("   ", tail[max(0, h - 400):h + 600][:1000])
        print("   ----")

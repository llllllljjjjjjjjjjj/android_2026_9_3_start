# -*- coding: utf-8 -*-
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
s = open(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\detail_ctx.json", encoding="utf-8", errors="replace").read()

# 所有 brand 相关字段
for m in re.finditer(r'"([A-Za-z_]*brand[A-Za-z_]*)"\s*:', s):
    k = m.group(1)
    ctx = s[max(0, m.start() - 60):m.start() + 300].replace(chr(10), " ")
    print(f"[{k}] @{m.start()}: ...{ctx[:340]}...")
    print()

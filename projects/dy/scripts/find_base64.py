# -*- coding: utf-8 -*-
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
s = open(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\detail_ctx.json", encoding="utf-8", errors="replace").read()
print("len", len(s))

# 1) data URI
for m in re.finditer(r"data:image/[a-z0-9+]+;base64,", s):
    print("DATA URI @", m.start(), s[max(0, m.start() - 120):m.start() + 120][:240])
    print()

# 2) 长 base64 字段值（>500 字符的 base64 串）
cands = []
for m in re.finditer(r'"([A-Za-z0-9_]+)"\s*:\s*"([A-Za-z0-9+/=]{600,})"', s):
    key, val = m.group(1), m.group(2)
    cands.append((key, len(val), m.start()))
for key, ln, pos in cands:
    print(f"BASE64-ish field {key} len={ln} @{pos}")
    print("   head:", s[pos:pos + 160])
    print()

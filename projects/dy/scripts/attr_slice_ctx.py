# -*- coding: utf-8 -*-
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
s = open(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\detail_ctx.json", encoding="utf-8", errors="replace").read()
i = s.find("property_name_all")
seg = s[i - 20000:i + 40000]
# 找 slice 结构
for m in re.finditer(r'"slice_id":"([^"]+)"', seg):
    print("slice:", m.group(1))
print("---- urls in attr window ----")
for m in re.finditer(r'https?://[^"\s\\]{10,600}?\.(?:png|jpg|jpeg|webp|heic|gif)[^"\s\\]*', seg):
    print("  ", m.group(0)[:200])
print("---- keys near attr ----")
keys = re.findall(r'"([A-Za-z_][A-Za-z0-9_]*)"\s*:', seg)
from collections import Counter
for k, c in Counter(keys).most_common(60):
    print(f"  {c:3d} {k}")

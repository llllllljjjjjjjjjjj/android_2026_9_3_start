# -*- coding: utf-8 -*-
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
s = open(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\detail_ctx.json", encoding="utf-8", errors="replace").read()
i = s.find("property_name_all")
tail = s[i:]
print("tail len", len(tail))

# tail 里的全部 key 统计
keys = Counter(re.findall(r'"([A-Za-z_][A-Za-z0-9_]*)"\s*:', tail))
for k, c in keys.most_common(80):
    print(f"  {c:3d} {k}")

print("---- image urls in tail ----")
urls = set(re.findall(r'https?://[^"\s\\]{10,900}?\.(?:png|jpg|jpeg|webp|heic|gif)[^"\s\\]*', tail))
for u in urls:
    print("  ", u[:200])

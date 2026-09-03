# -*- coding: utf-8 -*-
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
s = open(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\detail_ctx.json", encoding="utf-8", errors="replace").read()
print("len", len(s))
# 找 attr 字段附近完整结构
i = s.find('property_name_all')
print("attr @", i)
seg = s[max(0, i - 3000):i + 3000]
print(seg[:6000])

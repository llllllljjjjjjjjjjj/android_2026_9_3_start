# -*- coding: utf-8 -*-
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
raw = open(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\b64\b64_01_0x706c4a5f36.txt", encoding="utf-8", errors="replace").read()
print("len", len(raw))
for pat, name in [(r"iVBORw0KGgo[A-Za-z0-9+/=]{200,}", "PNG"),
                  (r"UklGR[A-Za-z0-9+/=]{200,}", "WEBP"),
                  (r"/9j/[A-Za-z0-9+/=]{200,}", "JPEG")]:
    ms = list(re.finditer(pat, raw))
    print(name, len(ms))
    for m in ms[:5]:
        print("  @", m.start())

# 每个图片前的字段名
for m in re.finditer(r"/9j/[A-Za-z0-9+/=]{100,}", raw):
    pre = raw[: m.start()]
    # 向前找最后一个 "key":"
    fm = list(re.finditer(r'"([A-Za-z_][A-Za-z0-9_]*)":\s*"', pre))
    if fm:
        fname = fm[-1].group(1)
        print("jpeg field:", fname)
    break

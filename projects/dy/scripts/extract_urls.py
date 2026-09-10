# -*- coding: utf-8 -*-
"""从 url_dump.txt 提炼唯一搜索 URL 样本，然后可安全删除原文件"""
import os

D = r"D:\reserve_agent\android\projects\dy\capture"
src = os.path.join(D, "url_dump.txt")
raw = open(src, "rb").read()

txt = None
for enc in ("utf-8", "utf-16", "gbk"):
    try:
        txt = raw.decode(enc)
        break
    except Exception:
        continue
if txt is None:
    txt = raw.decode("utf-8", errors="ignore")

uniq, seen = [], set()
for line in txt.splitlines():
    i = line.find("@@URLTXT ")
    if i < 0:
        continue
    u = line[i + 9:].strip()
    if "/search" in u and u not in seen:
        seen.add(u)
        uniq.append(u)

out = os.path.join(D, "url_samples.txt")
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(uniq))

print("unique search URLs:", len(uniq))
for u in uniq[:6]:
    print("   ", u[:130])

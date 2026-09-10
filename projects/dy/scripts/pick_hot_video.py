# -*- coding: utf-8 -*-
"""从已有搜索结果里挑评论最多的视频（用于验证评论翻页）"""
import json, glob, os

D = r"D:\reserve_agent\android\projects\dy\capture"
rows = []
for f in glob.glob(os.path.join(D, "results_*.json")):
    try:
        data = json.load(open(f, encoding="utf-8"))
    except Exception:
        continue
    for c in data:
        try:
            n = int(c.get("comment") or 0)
        except Exception:
            n = 0
        if n > 0 and c.get("aid"):
            rows.append((n, c["aid"], (c.get("desc") or "")[:36], os.path.basename(f)))

rows.sort(reverse=True)
print("评论数 Top 12：")
for n, aid, desc, src in rows[:12]:
    print(f"  {n:>7}  {aid}  {desc}   [{src}]")
print()
print("最高评论数视频 aid =", rows[0][1] if rows else None, "评论数 =", rows[0][0] if rows else None)

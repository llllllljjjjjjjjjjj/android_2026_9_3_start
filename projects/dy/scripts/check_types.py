# -*- coding: utf-8 -*-
"""检查现有搜索结果里的 awemeType 分布 + 是否有图文（判据：无 playUrl / 非 0 type）"""
import json, glob, os, collections

D = r"D:\reserve_agent\android\projects\dy\capture"
files = sorted(glob.glob(os.path.join(D, "results_*.json")))
types = collections.Counter()
no_play = []
total = 0

for f in files:
    try:
        data = json.load(open(f, encoding="utf-8"))
    except Exception:
        continue
    for c in data:
        total += 1
        t = c.get("awemeType")
        types[str(t)] += 1
        if t not in ("0", None):
            no_play.append((os.path.basename(f), c.get("aid"), t, (c.get("desc") or "")[:40]))

print("total cards:", total)
print("awemeType distribution:", dict(types))
print("\nnon-zero type samples:")
for x in no_play[:10]:
    print("   ", x)

# videos.json 的结构样本
vp = os.path.join(D, "videos.json")
if os.path.exists(vp):
    v = json.load(open(vp, encoding="utf-8"))
    print("\nvideos.json items:", len(v))
    for it in v[:3]:
        print("   keys:", list(it.keys()))
        print("   playUrl:", (it.get("playUrl") or ["<none>"])[0][:80])

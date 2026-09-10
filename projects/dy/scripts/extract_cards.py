# -*- coding: utf-8 -*-
"""把 hook 抓到的搜索结果卡片提取为 UTF-8 JSON（处理 PowerShell 输出编码）"""
import json, os, re

SRC = r"D:\reserve_agent\android\projects\dy\capture\searchcard2.txt"
OUT = r"D:\reserve_agent\android\projects\dy\capture\search_results_compass.json"


def read_text(path):
    raw = open(path, "rb").read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", errors="ignore")
    if raw[:3] == b"\xef\xbb\xbf":
        return raw.decode("utf-8-sig", errors="ignore")
    for enc in ("utf-8", "gbk", "utf-16"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


txt = read_text(SRC)
cards = []
for line in txt.splitlines():
    i = line.find("@@CARD {")
    if i < 0:
        continue
    frag = line[i + len("@@CARD "):].strip()
    try:
        cards.append(json.loads(frag))
    except Exception:
        continue

# 去重（按 aid）
uniq = {}
for c in cards:
    if c.get("aid"):
        uniq[c["aid"]] = c

out = list(uniq.values())
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print(f"cards parsed: {len(cards)}, unique: {len(out)} -> {OUT}\n")
for c in out[:12]:
    d = (c.get("desc") or "")[:60].replace("\n", " ")
    print(f"  aid={c.get('aid')}  digg={c.get('digg')}  desc={d}")

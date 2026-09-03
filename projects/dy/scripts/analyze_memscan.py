# -*- coding: utf-8 -*-
# analyze_memscan.py — 分析内存扫描 JSON 片段：字段统计 + 关键词定位
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "capture" / "memscan_json"

KEYWORDS = ["qualification", "brand", "spec", "parameter", "param", "certificate", "license",
            "authorize", "cert", "资", "品牌", "资质"]

fields = {}
for f in sorted(D.glob("json_*.txt")):
    raw = f.read_text(encoding="utf-8", errors="replace")
    # 所有 \"xxx\": 形式的 key（转义 JSON 或原生 JSON 都有）
    for m in re.finditer(r'\\?"([A-Za-z_][A-Za-z0-9_.]*)":', raw):
        k = m.group(1)
        fields[k] = fields.get(k, 0) + 1
    for m in re.finditer(r'(?<![\\\w])"([a-z_][a-z0-9_]*)"\s*:', raw):
        k = m.group(1)
        fields[k] = fields.get(k, 0) + 1

top = sorted(fields.items(), key=lambda kv: -kv[1])
print("== top 120 fields ==")
for k, v in top[:120]:
    print(f"{v:5d}  {k}")

print("\n== keyword-related fields ==")
for k, v in top:
    if any(kw in k.lower() for kw in ["qualif", "brand", "spec", "param", "cert", "license", "author"]):
        print(f"{v:5d}  {k}")

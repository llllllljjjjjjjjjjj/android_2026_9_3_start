# -*- coding: utf-8 -*-
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BIN = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\urldump.bin")
data = BIN.read_bytes()

# 资质图片数据块在 0x9e2xxx-0x9e4xxx。读前面 0x9d0000-0x9e3000 找字段名和接口
for start, end, label in [
    (0x9e0000, 0x9e3000, "数据块前"),
    (0x9e2e00, 0x9e5000, "数据块内"),
]:
    chunk = data[start:end]
    # 提取可读 ASCII 字符串（字段名/URL）
    strs = re.findall(rb"[a-zA-Z_][a-zA-Z0-9_:/\.\-]{4,80}", chunk)
    seen = []
    for s in strs:
        t = s.decode("ascii", errors="ignore")
        if t not in seen and any(k in t for k in ("qualif", "license", "brand", "image", "url", "http", "ecombd", "cert", "auth", "shop", "product", "property", "title", "type", "uri")):
            seen.append(t)
    print(f"\n=== {label} @{start:#x}-{end:#x}: 关键字符串 ===")
    for t in seen[:60]:
        print("  ", t)

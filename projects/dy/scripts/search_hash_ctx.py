# -*- coding: utf-8 -*-
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BIN = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\urldump.bin")
data = BIN.read_bytes()

# 资质图片 hash（多个样本）
hashes = ["7c796d3c625242c48270c52ae764cc67", "93d75646201a4f1588ed4d0920c7b786",
          "21a1df5d420d48bea0a9c998c1a20282", "e52d68cbfa794d2aa423484f2a7b13eb",
          "88ed4d0920c7b786"]

# 找 hash 出现的上下文，看是否有接口 URL / 响应 JSON 特征
for h in hashes:
    pat = h.encode()
    hits = list(re.finditer(re.escape(pat), data))
    print(f"\n== hash {h}: {len(hits)} hits")
    for m in hits[:3]:
        off = m.start()
        a = max(0, off - 400)
        b = min(len(data), off + 200)
        chunk = data[a:b]
        txt = chunk.decode("utf-8", errors="replace")
        txt = txt.replace("\n", " ").replace("\x00", " ")
        # 找附近的 URL 和字段名
        print(f"   @{off:#x}: ...{txt[-250:]}...")
        # 检查附近是否有 https:// 或字段名
        nearby = data[max(0, off - 800):off]
        urls = re.findall(rb"https?://[^\x00\"'\s]{5,120}", nearby)
        if urls:
            print(f"     附近URL: {[u.decode('utf-8', 'replace')[:100] for u in urls[-3:]]}")

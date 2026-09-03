# -*- coding: utf-8 -*-
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BIN = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\memdump.bin")
data = BIN.read_bytes()

# 完整键串和值串（逗号分隔）
keys_full = "适用人群,包装类型,品牌,注册人/备案人的名称"
vals_full = "普通人群,普通装,溪木源,诺德溯源（广州）生物科技有限公司"

for label, s in [("keys_full", keys_full), ("vals_full", vals_full)]:
    for enc, tag in [(s.encode("utf-16-le"), "utf16"), (s.encode(), "utf8")]:
        hits = list(re.finditer(re.escape(enc), data))
        print(f"{label} {tag}: {len(hits)} hits")
        for m in hits[:2]:
            off = m.start()
            if tag == "utf16":
                al = off - (off % 2)
                txt = data[al:al+len(s)*2*2].decode("utf-16-le", errors="replace")
                print(f"   @{off:#x}: {txt[:200]}")
            else:
                txt = data[off:off+400].decode("utf-8", errors="replace")
                print(f"   @{off:#x}: {txt[:200]}")

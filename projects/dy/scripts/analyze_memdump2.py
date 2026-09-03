# -*- coding: utf-8 -*-
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BIN = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\memdump.bin")
data = BIN.read_bytes()
print("size", len(data))

cns = ["普通人群", "普通装", "溪木源", "诺德溯源", "粤G妆网备字", "层孔菌提取物",
       "混合性肤质", "舒缓肌肤", "中国大陆", "正装", "保质期", "适用人群", "包装类型", "品牌"]

for cn in cns:
    u8 = cn.encode()
    u16 = cn.encode("utf-16-le")
    n8 = len(re.findall(re.escape(u8), data))
    n16 = len(re.findall(re.escape(u16), data))
    print(f"{cn:12s} utf8={n8} utf16={n16}")

# 输出第一个命中的上下文（优先 utf16，因为 Java 渲染）
print("\n=== context samples ===")
for cn in ["普通人群", "溪木源", "粤G妆网备字"]:
    for enc, tag in [(cn.encode("utf-16-le"), "utf16"), (cn.encode(), "utf8")]:
        m = re.search(re.escape(enc), data)
        if m:
            off = m.start()
            print(f"\n--- {cn} {tag} @ {off:#x}")
            if tag == "utf16":
                al = off - (off % 2)
                txt = data[max(0, al-400):al+800].decode("utf-16-le", errors="replace")
            else:
                txt = data[max(0, off-200):off+600].decode("utf-8", errors="replace")
            print(txt[:600])
            break

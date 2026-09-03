# -*- coding: utf-8 -*-
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BIN = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\memdump.bin")

data = BIN.read_bytes()
print("size", len(data))

# UTF-8 明文
pat_utf8 = b'"property_name_all"'
# UTF-16LE
pat_utf16 = "property_name_all".encode("utf-16-le")

hits = []
for m in re.finditer(re.escape(pat_utf8), data):
    hits.append(("utf8", m.start()))
for m in re.finditer(re.escape(pat_utf16), data):
    hits.append(("utf16", m.start()))

print("utf8 hits:", sum(1 for k, _ in hits if k == "utf8"))
print("utf16 hits:", sum(1 for k, _ in hits if k == "utf16"))

for kind, off in hits[:8]:
    print(f"\n=== {kind} @ {off:#x}")
    a = max(0, off - 80)
    b = min(len(data), off + 500)
    chunk = data[a:b]
    if kind == "utf16":
        # 对齐偶数偏移
        al = off - (off % 2)
        txt = data[al:b].decode("utf-16-le", errors="replace")
        print("UTF16 text:", txt[:300])
    else:
        txt = chunk.decode("utf-8", errors="replace")
        print("UTF8 text:", txt[:300])

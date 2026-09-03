# -*- coding: utf-8 -*-
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BIN = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\urldump.bin")
data = BIN.read_bytes()
print("size", len(data))

pats = [
    (b"images_show_panel", "utf8"),
    (b"qualification", "utf8"),
    (b"license", "utf8"),
    (b"brand_qual", "utf8"),
    ("资质".encode("utf-8"), "utf8-cn"),
    ("授权".encode("utf-8"), "utf8-cn"),
    ("资质".encode("utf-16-le"), "utf16-cn"),
    ("授权".encode("utf-16-le"), "utf16-cn"),
]

for pat, tag in pats:
    hits = list(re.finditer(re.escape(pat), data))
    print(f"\n== {tag} {pat!r}: {len(hits)} hits")
    for m in hits[:3]:
        off = m.start()
        a = max(0, off - 150)
        b = min(len(data), off + 400)
        chunk = data[a:b]
        if tag.startswith("utf16"):
            txt = chunk.decode("utf-16-le", errors="replace")
        else:
            txt = chunk.decode("utf-8", errors="replace")
        txt = txt.replace("\n", " ")
        print(f"   @{off:#x}: {txt[:300]}")

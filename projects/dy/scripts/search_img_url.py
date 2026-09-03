# -*- coding: utf-8 -*-
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BIN = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\urldump.bin")
data = BIN.read_bytes()

# 搜图片桶名，找完整 URL
for pat, tag in [(b"6vegkygxbk", "utf8"), ("6vegkygxbk".encode("utf-16-le"), "utf16"),
                 (b"tos-cn-i-6veg", "utf8"), (b"fe_reactlynx_ecommerce_images_show_panel", "utf8")]:
    hits = list(re.finditer(re.escape(pat), data))
    print(f"\n== {tag} {pat!r}: {len(hits)} hits")
    for m in hits[:4]:
        off = m.start()
        a = max(0, off - 200)
        b = min(len(data), off + 500)
        chunk = data[a:b]
        if tag == "utf16":
            al = off - (off % 2)
            txt = data[max(0, al - 200):al + 600].decode("utf-16-le", errors="replace")
        else:
            txt = chunk.decode("utf-8", errors="replace")
        txt = txt.replace("\n", " ").replace("\x00", " ")
        print(f"   @{off:#x}: {txt[:350]}")

# -*- coding: utf-8 -*-
import base64
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
D = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\b64")
OUT = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\b64_imgs")
OUT.mkdir(exist_ok=True)

for f in D.glob("b64_*.txt"):
    raw = f.read_text(encoding="utf-8", errors="replace")
    print("file", f.name, "len", len(raw))
    # 提取 base64 串（长串）
    cands = re.findall(r'[A-Za-z0-9+/=]{1000,}', raw)
    print("  long b64 candidates:", len(cands))
    for i, c in enumerate(cands):
        try:
            data = base64.b64decode(c, validate=False)
        except Exception:
            continue
        kind = ""
        if data[:4] == b"\xff\xd8\xff\xe0" or data[:3] == b"\xff\xd8\xff":
            kind = "jpg"
        elif data[:8] == b"\x89PNG\r\n\x1a\n":
            kind = "png"
        elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            kind = "webp"
        elif data[4:8] == b"ftyp":
            kind = "heic"
        if kind:
            fn = OUT / f"{f.stem}_{i}.{kind}"
            fn.write_bytes(data)
            print(f"  -> SAVED {fn.name} {len(data)}B")

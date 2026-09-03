# -*- coding: utf-8 -*-
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
D = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\qualbig")
for f in sorted(D.glob("qual_*.json")):
    raw = f.read_text(encoding="utf-8", errors="replace")
    urls = re.findall(r"https?:\\?/\\?/[^\"\s\\]{10,700}?\.(?:png|jpg|jpeg|webp|heic|gif)[^\"\s\\]*", raw)
    urls = [u.replace("\\/", "/") for u in urls]
    if urls:
        print("==", f.name, len(urls), "urls ==")
        for u in dict.fromkeys(urls):
            print("  ", u[:220])

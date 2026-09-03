# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SRC = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\memdump")

counts = {}
samples = {}
for seg in sorted(SRC.glob("seg_*.bin")):
    data = seg.read_bytes()
    for magic, name in [(b"RIFF", "RIFF"), (b"WEBP", "WEBP"), (b"ftyp", "ftyp(heic)"),
                        (b"\x89PNG", "PNG"), (b"\xff\xd8\xff", "JPEG")]:
        n = data.count(magic)
        if n:
            counts[name] = counts.get(name, 0) + n
            if name not in samples and magic == b"RIFF":
                i = data.find(magic)
                samples[name] = data[max(0, i - 4):i + 40]

print(counts)
for k, v in samples.items():
    print(k, v)

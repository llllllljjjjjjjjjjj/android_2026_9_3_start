# -*- coding: utf-8 -*-
# extract_imgs_from_dump.py — 扫描内存 dump 段，提取完整图片文件（webp/png/jpeg/heic）
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SRC = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\memdump")
DST = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\extracted_imgs")
DST.mkdir(exist_ok=True)

MAGICS = {
    b"RIFF": ("webp", None),
    b"\x89PNG\r\n\x1a\n": ("png", None),
    b"\xff\xd8\xff": ("jpg", None),
    b"\x00\x00\x00\x18ftyp": ("heic", None),
    b"\x00\x00\x00 ftyp": ("heic", None),
    b"ftyp": ("heic_raw", None),  # ftyp 盒子非标准偏移
}

CHUNK = 4 * 1024 * 1024
found = []

def scan_file(f: Path):
    size = f.stat().st_size
    if size < 2000:
        return
    with open(f, "rb") as fh:
        # 简单粗暴：全文件扫描 magic 并尝试提取
        data = fh.read()
    # 在文件中找各 magic 位置
    positions = []
    for magic, (kind, _) in MAGICS.items():
        pos = 0
        while True:
            i = data.find(magic, pos)
            if i < 0:
                break
            if kind == "heic_raw" and i < 4:
                # ftyp 前应有 box size，往前看
                pass
            # 检查前面的 box size 字段（heic）
            if kind in ("heic", "heic_raw"):
                bs = data[i - 4:i]
                if len(bs) == 4:
                    boxsize = int.from_bytes(bs, "big")
                    if 10 < boxsize < 8 * 1024 * 1024:
                        start = i - 4
                        positions.append((start, "heic", boxsize))
                pos = i + 4
                continue
            # webp: RIFF <size> WEBP
            if kind == "webp":
                if data[i:i + 4] == b"RIFF" and data[i + 8:i + 12] == b"WEBP":
                    sz = int.from_bytes(data[i + 4:i + 8], "little")
                    if 1000 < sz + 8 < 8 * 1024 * 1024:
                        positions.append((i, "webp", sz + 8))
                pos = i + 4
                continue
            positions.append((i, kind, None))
            pos = i + 8

    for idx, (start, kind, known) in enumerate(positions):
        # 决定长度
        if known:
            length = known
        else:
            # 找下一个 magic 或者到文件尾
            nxt = min([p for p, _, _ in positions if p > start], default=size)
            length = min(nxt - start, 8 * 1024 * 1024)
        if length < 1000:
            continue
        blob = data[start:start + length]
        # 校验 PNG 尾 / JPEG 尾 / webp 大小
        if kind == "png" and not blob.endswith(b"IEND\xaeB`\x82"):
            continue
        out = DST / f"{f.stem}_{start:x}_{kind}.{kind if kind != 'heic_raw' else 'heic'}"
        out.write_bytes(blob)
        found.append((out, length, kind))


for seg in sorted(SRC.glob("seg_*.bin")):
    scan_file(seg)

print(f"extracted {len(found)} images -> {DST}")
for out, length, kind in found:
    print(f"  {out.name}  {length//1024}KB  {kind}")

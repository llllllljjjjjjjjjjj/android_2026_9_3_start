# -*- coding: utf-8 -*-
"""诊断下载的图片文件真实格式"""
import os, binascii

p = r"D:\reserve_agent\android\projects\dy\capture\videos\7665610765634568613_img01.jpg"
d = open(p, "rb").read()
print("size:", len(d))
print("head hex:", d[:64].hex())
print("head ascii:", "".join(chr(b) if 32 <= b < 127 else "." for b in d[:64]))
print()

# 常见格式魔数
sigs = {
    "JPEG": b"\xff\xd8\xff",
    "PNG": b"\x89PNG",
    "GIF": b"GIF8",
    "WEBP/RIFF": b"RIFF",
    "BMP": b"BM",
    "HEIC/ISOBMFF": b"ftyp",
    "MP4-ish": b"\x00\x00\x00",
    "HTML": b"<",
    "JSON": b"{",
}
for name, sig in sigs.items():
    print(f"  {name}: {d.startswith(sig)}")

# 找 ftyp box（可能带偏移）
i = d.find(b"ftyp")
print("\nftyp offset:", i)
if i >= 0:
    print("  brand:", d[i + 4:i + 12])

# 是否 gzip / br / zstd
print("\ngzip:", d[:2] == b"\x1f\x8b", "| zstd:", d[:4] == b"\x28\xb5\x2f\xfd")
print("first 200 ascii:", "".join(chr(b) if 32 <= b < 127 else "." for b in d[:200]))

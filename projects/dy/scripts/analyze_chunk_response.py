# -*- coding: utf-8 -*-
"""分析协议直发的 chunk 流响应（ChunkDataStream 分块协议）"""
import gzip, zlib, os, json, re

P = r"D:\reserve_agent\android\projects\dy\capture\direct_comment_response.txt"
raw = open(P, "rb").read()
print(f"len={len(raw)}")
print(f"hex: {raw[:64].hex()}")
print(f"ascii: {''.join(chr(b) if 32 <= b < 127 else '.' for b in raw)}")
print()

# 分块协议探测
print("--- 格式探测 ---")
print(f"gzip: {raw[:2] == b'\\x1f\\x8b'}")
print(f"zlib: {raw[:2] in (b'\\x78\\x01', b'\\x78\\x9c', b'\\x78\\xda')}")
print(f"brotli hint: {raw[:4] == b'\\x28\\xb5\\x2f\\xfd'}")
print(f"zstd hint: {raw[:4] == b'\\x04\\x22\\x4d\\x18'}")
print(f"JSON: {raw[:1] in (b'{', b'[')}")
print(f"ASCII 可读率: {sum(1 for b in raw if 32 <= b < 127) / len(raw):.2f}")

# 尝试各种解码
for name, fn in [
    ("zlib", lambda d: zlib.decompress(d)),
    ("gzip", lambda d: gzip.decompress(d)),
    ("raw-deflate", lambda d: zlib.decompress(d, -15)),
]:
    try:
        out = fn(raw)
        print(f"\n[{name}] 解压成功 len={len(out)}")
        print(f"  head: {out[:300]}")
        break
    except Exception as e:
        print(f"[{name}] 失败: {type(e).__name__}")

# 试 brotli
try:
    import brotli
    out = brotli.decompress(raw)
    print(f"\n[brotli] 成功 len={len(out)}")
    print(f"  head: {out[:400]}")
except Exception as e:
    print(f"[brotli] 失败: {type(e).__name__} {e}")

# 找内嵌 JSON
m = re.search(rb'\{.*\}', raw, re.S)
if m:
    print(f"\n[内嵌 JSON] {m.group(0)[:300]}")

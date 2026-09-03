# -*- coding: utf-8 -*-
# parse_charles_search.py — 从 Charles 会话导出中提取搜索请求（URL + 完整 body）v2
# 条目结构: 顶层 host/path/query + request{body{kind,encoded,size}} / response
import base64
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SESSION = ROOT / "capture" / "charles_session4.json"
if not SESSION.exists():
    SESSION = ROOT / "capture" / "charles_session.json"
OUTDIR = ROOT / "capture" / "search_bodies"
OUTDIR.mkdir(exist_ok=True)

try:
    import zstandard as zstd
    zstd_ok = True
except ImportError:
    zstd_ok = False

data = json.loads(SESSION.read_text(encoding="utf-8-sig"))
print(f"[*] session entries: {len(data)}")

KEYWORDS = ("search5-search", "search/general", "search/sug", "general/single",
            "general/stream", "refresh_related", "suggest_words", "search/memory")

search_idx = 0
for i, e in enumerate(data):
    host = e.get("host") or ""
    path = e.get("path") or ""
    url = host + path
    if not any(k in url for k in KEYWORDS):
        continue
    req = e.get("request") or {}
    body = req.get("body")
    print(f"\n[{i}] {e.get('method', '?')} {e.get('status', '?')} {host}{path}")
    q = (e.get("query") or "")[:120]
    if q:
        print(f"    query: {q}")
    if isinstance(body, dict):
        kind = body.get("kind", "?")
        enc = body.get("encoded", "")
        size = body.get("size", 0)
        print(f"    body kind={kind} size={size} b64len={len(enc)}")
        if enc:
            try:
                raw = base64.b64decode(enc)
            except Exception as ex:
                print(f"    b64 fail: {ex}")
                continue
            search_idx += 1
            name = f"charles_{search_idx}_{size}b.bin"
            (OUTDIR / name).write_bytes(raw)
            print(f"    saved {name} raw={len(raw)}B")
            plain, pk = None, ""
            if raw.startswith(b"\x1f\x8b"):
                try:
                    plain, pk = gzip.decompress(raw), "gzip"
                except Exception:
                    pass
            elif raw.startswith(b"\x28\xb5\x2f\xfd") and zstd_ok:
                try:
                    plain, pk = zstd.ZstdDecompressor().decompress(raw), "zstd"
                except Exception:
                    pass
            if plain:
                (OUTDIR / name.replace(".bin", f".{pk}")).write_bytes(plain)
                kw = [w for w in (b"meishi", b"\xe7\xbe\x8e\xe9\xa3\x9f", b"keyword", b"search_id") if w in plain]
                print(f"    decompressed {pk} {len(plain)}B kw={kw}")
                for w in (b"meishi", b"\xe7\xbe\x8e\xe9\xa3\x9f", b"keyword"):
                    if w in plain:
                        idx = plain.find(w)
                        print("    [HEX@kw] " + plain[max(0, idx - 64):idx + 160].hex())
                        print("    [TXT@kw] " + repr(plain[max(0, idx - 96):idx + 192]))
                        break
            else:
                print("    raw head: " + raw[:96].hex())
    elif body:
        print(f"    body raw len={len(body)} head={body[:64].hex() if isinstance(body, bytes) else str(body)[:120]}")

print(f"\n[*] search bodies saved: {search_idx}")

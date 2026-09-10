# -*- coding: utf-8 -*-
"""解压 SSL 流里的 gzip 响应，提取搜索结果 JSON"""
import re, zlib, json, os

P = r"D:\reserve_agent\android\projects\dy\capture\resp_stream.bin"
OUT = r"D:\reserve_agent\android\projects\dy\capture"
raw = open(P, "rb").read()
print("total:", len(raw))

results = []
for m in re.finditer(b"\x1f\x8b\x08", raw):
    off = m.start()
    d = zlib.decompressobj(31)  # gzip
    try:
        out = d.decompress(raw[off:off + 3_000_000])
        out += d.flush()
    except Exception as e:
        # 容忍截断：逐块喂
        out = b""
        dd = zlib.decompressobj(31)
        step = 4096
        for i in range(off, min(off + 3_000_000, len(raw)), step):
            try:
                out += dd.decompress(raw[i:i + step])
            except Exception:
                break
        try:
            out += dd.flush()
        except Exception:
            pass
    if out:
        results.append((off, len(out), out))

print(f"decompressed blocks: {len(results)}")
results.sort(key=lambda x: -x[1])
for off, ln, out in results[:8]:
    head = out[:120].decode("utf-8", "ignore").replace("\n", " ")
    print(f"  off={off} len={ln} head={head[:100]}")

# 找含搜索数据的最大块
best = None
for off, ln, out in results:
    if b"aweme_list" in out or b'"desc"' in out or b"search_id" in out:
        if best is None or ln > best[1]:
            best = (off, ln, out)

if best:
    off, ln, out = best
    p1 = os.path.join(OUT, "search_result_decompressed.json")
    open(p1, "wb").write(out)
    print(f"\n[SAVED] {p1} ({ln} B)")
    try:
        j = json.loads(out.decode("utf-8", "ignore"))
        print("top keys:", list(j.keys())[:20])
        for k in ("aweme_list", "data", "log_pb", "search_id", "cursor", "has_more"):
            if k in j:
                v = j[k]
                print(f"  {k}: {type(v).__name__}" + (f" len={len(v)}" if isinstance(v, (list, dict)) else f" = {str(v)[:80]}"))
        al = j.get("aweme_list") or (j.get("data") or {}).get("aweme_list")
        if isinstance(al, list) and al:
            print(f"\n  ★ aweme_list 条目数: {len(al)}")
            it = al[0]
            print("  item keys:", list(it.keys())[:14])
            if "desc" in it:
                print("  desc:", str(it["desc"])[:100])
            if "aweme_id" in it:
                print("  aweme_id:", it["aweme_id"])
            if "statistics" in it:
                print("  statistics:", str(it["statistics"])[:120])
    except Exception as e:
        print("parse err:", e)
else:
    print("\nno search-result block found in decompressed data")
    # 落盘前3个解压块供人工检查
    for i, (off, ln, out) in enumerate(results[:3]):
        p = os.path.join(OUT, f"decomp_{i}_{off}.bin")
        open(p, "wb").write(out)
        print(f"  saved {p} ({ln} B) head={out[:80]}")

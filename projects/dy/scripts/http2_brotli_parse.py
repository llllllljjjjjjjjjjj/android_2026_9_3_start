# -*- coding: utf-8 -*-
"""解析 HTTP/2 帧 + brotli 解压，提取搜索响应 JSON"""
import brotli, json, os, re

P = r"D:\reserve_agent\android\projects\dy\capture\resp_stream.bin"
OUT = r"D:\reserve_agent\android\projects\dy\capture"
raw = open(P, "rb").read()
print("stream:", len(raw))

# 1) 滑动解析 HTTP/2 帧（length(3) type(1) flags(1) sid(4)）
FRAME_TYPES = {0: "DATA", 1: "HEADERS", 2: "PRIORITY", 3: "RST", 4: "SETTINGS",
               5: "PUSH", 6: "PING", 7: "GOAWAY", 8: "WINDOW_UPDATE", 9: "CONTINUATION"}
frames = []
i = 0
while i + 9 <= len(raw):
    ln = int.from_bytes(raw[i:i+3], "big")
    typ = raw[i+3]
    fl = raw[i+4]
    sid = int.from_bytes(raw[i+5:i+9], "big") & 0x7fffffff
    if typ in FRAME_TYPES and ln < 200000 and i + 9 + ln <= len(raw):
        frames.append((i, ln, typ, fl, sid))
        i += 9 + ln
    else:
        i += 1

from collections import Counter
print("frames parsed:", len(frames), Counter(FRAME_TYPES.get(f[2]) for f in frames).most_common(8))

# 2) 对 DATA 帧 payload 尝试 brotli 解压
ok = 0
found = []
for off, ln, typ, fl, sid in frames:
    if typ != 0 or ln == 0:      # DATA
        continue
    payload = raw[off+9:off+9+ln]
    for attempt in (payload, payload[1:], payload[2:], payload[4:]):
        if len(attempt) < 8:
            continue
        try:
            dec = brotli.decompress(attempt)
        except Exception:
            continue
        ok += 1
        txt = dec.decode("utf-8", "ignore")
        if re.search(r"aweme_list|aweme_id|\"desc\"|search_id|card_name", txt):
            found.append((off, ln, len(dec), txt))
        break

print("brotli-decompressed DATA frames:", ok)
print("frames containing search data:", len(found))

if found:
    found.sort(key=lambda x: -x[2])
    off, ln, dl, txt = found[0]
    p = os.path.join(OUT, "search_result_from_br.json")
    open(p, "w", encoding="utf-8").write(txt)
    print(f"[SAVED] {p} ({dl} B)")
    try:
        j = json.loads(txt)
        print("top keys:", list(j.keys())[:20])
        al = j.get("aweme_list") or (j.get("data") or {}).get("aweme_list") or j.get("data")
        if isinstance(al, list) and al:
            print(f"aweme_list len: {len(al)}")
            it = al[0]
            if isinstance(it, dict):
                print("item keys:", list(it.keys())[:12])
                print("desc:", str(it.get("desc"))[:90])
                print("aweme_id:", it.get("aweme_id"))
    except Exception as e:
        print("parse err:", e, "| head:", txt[:200])
else:
    # 落盘所有成功解压的块，供检查
    n = 0
    for off, ln, typ, fl, sid in frames:
        if typ != 0 or ln == 0:
            continue
        payload = raw[off+9:off+9+ln]
        for attempt in (payload, payload[1:], payload[2:], payload[4:]):
            try:
                dec = brotli.decompress(attempt)
            except Exception:
                continue
            p = os.path.join(OUT, f"br_dec_{off}.txt")
            open(p, "wb").write(dec)
            print("  saved", p, len(dec), "head:", dec[:80])
            n += 1
            break
        if n >= 5:
            break
    print("dumped", n, "decompressed blocks")

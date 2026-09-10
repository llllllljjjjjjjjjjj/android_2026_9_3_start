# -*- coding: utf-8 -*-
"""分析抓到的响应明文流：找搜索结果 JSON / 检测压缩"""
import re, os, gzip, io, json

P = r"D:\reserve_agent\android\projects\dy\capture\resp_stream.bin"
raw = open(P, "rb").read()
print("total bytes:", len(raw))

# 1) 压缩特征
print("gzip magic count:", raw.count(b"\x1f\x8b"))
print("br/zstd hints:", raw.count(b"\x28\xb5\x2f\xfd"), raw.count(b"\x04\x22\x4d\x18"))

# 2) 关键词命中位置
for kw in [b"aweme_list", b"aweme_id", b'"desc"', b"search_id", b"global_doodle_config", b"doc_dict", b"card_name", b"log_pb"]:
    idxs = [m.start() for m in re.finditer(re.escape(kw), raw)][:5]
    print(f"{kw.decode()}: {len(idxs)} hits -> {idxs}")

# 3) 尝试提取最大的 JSON 对象
def find_json_blocks(buf, limit=5):
    out = []
    for m in re.finditer(rb'\{"[a-z_]+":', buf):
        s = m.start()
        # 简单括号配对
        depth = 0
        i = s
        in_str = False
        esc = False
        while i < len(buf) and i - s < 400000:
            c = buf[i:i+1]
            if in_str:
                if esc: esc = False
                elif c == b"\\": esc = True
                elif c == b'"': in_str = False
            else:
                if c == b'"': in_str = True
                elif c == b"{": depth += 1
                elif c == b"}":
                    depth -= 1
                    if depth == 0:
                        out.append((s, i + 1, i + 1 - s))
                        break
            i += 1
        if len(out) >= limit:
            break
    return out

blocks = find_json_blocks(raw, 8)
print("\njson blocks (offset,len):")
for s, e, ln in blocks:
    print("  ", s, ln)
    seg = raw[s:e]
    if b"aweme_list" in seg or b'"desc"' in seg:
        print("   *** CONTAINS SEARCH RESULT DATA ***")

# 4) 保存含 aweme_list 的块
best = None
for s, e, ln in blocks:
    if b"aweme_list" in raw[s:e]:
        if best is None or ln > best[2]:
            best = (s, e, ln)
if best:
    s, e, ln = best
    outp = r"D:\reserve_agent\android\projects\dy\capture\searchresult_block.json"
    open(outp, "wb").write(raw[s:e])
    print(f"\n[SAVED] {outp} ({ln} B)")
    try:
        j = json.loads(raw[s:e].decode("utf-8", "ignore"))
        print("top keys:", list(j.keys())[:20])
        al = j.get("aweme_list") or (j.get("data") or {}).get("aweme_list")
        if al:
            print("aweme_list len:", len(al))
            print("first item desc:", str(al[0].get("desc"))[:80])
    except Exception as ex:
        print("parse err:", ex)

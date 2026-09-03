# -*- coding: utf-8 -*-
# replay_latest.py — 抓 Charles 最新评论请求 → oracle 签名 → 立即重放（一体化闭环）
#
# 变体：
#   python replay_latest.py oracle   ← oracle 八神签名 + 抓包新 stub（默认）
#   python replay_latest.py passth  ← 完全原样重放（含真实八神头，测试重放防护）
#   python replay_latest.py oracle2 ← oracle 签名 + 随机新 stub（测试 stub 新鲜度要求）
import base64
import json
import sys
import time
from pathlib import Path

import requests
import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]          # projects/dy
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "android_mcp" / "servers" / "charles_mcp"))
from charles_api import export_session

sys.path.insert(0, str(ROOT / "scripts"))
import comment_replay as cr


def get_latest_stream():
    """从 Charles 会话取最新一条 comment/list/stream 请求。"""
    entries = export_session()
    hits = [e for e in entries if "/comment/list/stream/" in (e.get("path") or "")]
    if not hits:
        raise SystemExit("会话中没有 comment/list/stream 请求，请先在抖音刷评论区")
    hit = max(hits, key=lambda e: e.get("times", {}).get("start", ""))
    url = f"https://{hit['host']}{hit['path']}?{hit['query']}"
    headers = {h["name"]: h["value"] for h in hit["request"]["header"]["headers"]
               if not h["name"].startswith(":")}
    body = base64.b64decode(hit["request"]["body"]["encoded"])
    ts = hit.get("times", {}).get("start", "")
    print(f"[0] 抓到最新请求 @ {ts}")
    print(f"    URL: {url[:150]}...")
    return url, headers, body


def oracle_sign(url, hdr_in):
    if cr._script is None:
        cr.oracle_connect()
    out = cr._script.exports_sync.oracle(url, hdr_in)
    parts = out.split("\r\n")
    sigs = {}
    for i in range(0, len(parts) - 1, 2):
        sigs[parts[i]] = parts[i + 1]
    return sigs


def send(url, headers, body):
    r = requests.post(url, headers=headers, data=body, timeout=20)
    print(f"[>] HTTP {r.status_code} | content-encoding: {r.headers.get('content-encoding')}")
    raw = r.content
    print(f"    {len(raw)} bytes")
    try:
        # 抖音响应：JSON 前有前缀、后有尾部数据 → raw_decode 只解第一个完整对象
        start = raw.find(b"{")
        if start > 0:
            raw = raw[start:]
        j, _ = json.JSONDecoder().raw_decode(raw.decode("utf-8", errors="replace"))
        print(f"    业务码: {j.get('status_code')} | msg: {j.get('status_msg')}")
        comments = j.get("comments") or []
        print(f"    comments: {len(comments)} 条 | has_more: {j.get('has_more')} | cursor: {j.get('cursor')}")
        for c in comments[:3]:
            print("     -", str(c.get("text", ""))[:50], "|", (c.get("user") or {}).get("nickname"))
        return j
    except Exception as e:
        print("    JSON 解析失败:", e, "| 前 200:", raw[:200].decode("utf-8", errors="replace"))
        return None


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "oracle"
    url, headers, body = get_latest_stream()

    if mode == "passth":
        print("[1] 完全原样重放（真实八神头）")
        send(url, headers, body)
        return

    # oracle 模式：八神头换 oracle 生成，其余头照抄
    hdr_in = cr.BASE_HDR + "\r\nx-ss-stub\r\n" + headers.get("x-ss-stub", "")
    if mode == "oracle2":
        # 随机新 stub（32 hex），看服务器是否要求 stub 与签名绑定为"新鲜生成"
        import secrets
        headers["x-ss-stub"] = secrets.token_hex(16).upper()
        hdr_in = cr.BASE_HDR + "\r\nx-ss-stub\r\n" + headers["x-ss-stub"]
    print(f"[1] oracle 签名中（mode={mode}，stub={headers.get('x-ss-stub','')[:12]}...）")
    sigs = oracle_sign(url, hdr_in)
    print("    oracle:", {k: v[:20] for k, v in sigs.items()})
    # 移除真实八神头，全部用 oracle 输出
    for k in list(headers):
        if k.lower() in ("x-argus", "x-gorgon", "x-helios", "x-khronos", "x-ladon", "x-medusa"):
            del headers[k]
    headers.update(sigs)
    # 时间戳类对齐 oracle 时钟
    headers["x-ss-req-ticket"] = str(int(time.time() * 1000))
    headers["activity_now_client"] = str(int(time.time() * 1000))
    j = send(url, headers, body)

    if mode == "page" and j:
        # 翻页验证：用响应里的 cursor 拉下一页
        #   query cursor → 新值；body session_id 第二段 → cursor；oracle 重新签名
        import re as _re
        next_cursor = j.get("cursor")
        if not next_cursor:
            print("[!] 响应无 cursor，无法翻页")
            return
        url2 = _re.sub(r"(?<=cursor=)\d+", str(next_cursor), url)
        # 重建 body：解 zstd → session_id 第二段换成 cursor → 重新压缩
        form = zstd.ZstdDecompressor().decompress(body).decode()
        form = _re.sub(r"(session_id=\d+)%3A\d+(%3A)", r"\1%3A" + str(next_cursor) + r"\2", form)
        body2 = zstd.ZstdCompressor().compress(form.encode())
        print(f"[2] 翻页: cursor={next_cursor} → oracle 重新签名（session_id={form[:60]}...）")
        sigs2 = oracle_sign(url2, hdr_in)
        headers2 = dict(headers)
        headers2.update(sigs2)
        headers2["x-ss-req-ticket"] = str(int(time.time() * 1000))
        headers2["activity_now_client"] = str(int(time.time() * 1000))
        send(url2, headers2, body2)


if __name__ == "__main__":
    main()

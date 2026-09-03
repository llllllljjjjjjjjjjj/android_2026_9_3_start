# -*- coding: utf-8 -*-
"""capture_comment_watch.py — 轮询 Charles 会话，捕获评论接口请求

每 8 秒导出一次 Charles 会话（Web Interface magic host），
发现 path/query 含 "comment" 的新请求后，把原始条目完整落盘：
    projects/dy/capture/comment_request.json
最多运行 15 分钟。
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "android_mcp" / "servers" / "charles_mcp"))
from charles_api import export_session, summarize

OUT = Path(__file__).resolve().parent.parent / "capture" / "comment_request.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

POLL_SEC = 8
DEADLINE = time.time() + 15 * 60
seen = set()
n_poll = 0
print(f"[watch] 开始轮询 Charles 会话，目标：path 含 comment 的请求 → {OUT}", flush=True)

try:
    while time.time() < DEADLINE:
        n_poll += 1
        try:
            entries = export_session(timeout=60)
        except Exception as e:
            print(f"[watch] #{n_poll} 导出失败: {e}", flush=True)
            time.sleep(POLL_SEC)
            continue

        fresh = [e for e in entries
                 if ("comment" in (e.get("path") or "").lower()
                     or "comment" in (e.get("query") or "").lower())
                 and e.get("status") not in ("RECEIVING_REQUEST_BODY", "WAITING_FOR_RESPONSE")]
        for e in fresh:
            key = (e.get("method"), e.get("host"), e.get("path"), e.get("query"))
            if key in seen:
                continue
            seen.add(key)
            s = summarize(e)
            print(f"[watch] #{n_poll} 命中: {s['method']} {s['url'][:160]}", flush=True)
            with open(OUT, "w", encoding="utf-8") as f:
                json.dump(e, f, ensure_ascii=False, indent=2)
            print(f"[watch] 原始条目已落盘 {OUT}（{len(json.dumps(e, ensure_ascii=False))} 字节）", flush=True)

        if n_poll % 15 == 0:
            print(f"[watch] #{n_poll} 会话 {len(entries)} 条，已见 comment 请求 {len(seen)} 个", flush=True)
        time.sleep(POLL_SEC)
except KeyboardInterrupt:
    pass
print(f"[watch] 结束。共轮询 {n_poll} 次，捕获 {len(seen)} 个 comment 请求。", flush=True)

# parse_session_logs.py — 通用会话日志索引器
# 功能：扫描 frida 会话日志，提取 [S] URL 行，按 endpoint 分类去重，
#       输出 parsed/urls_by_endpoint.json 与 INDEX.md（endpoint → 文件:行号引用）。
# 用法：python parse_session_logs.py <日志文件...>
import re
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
CAPTURE = os.path.normpath(os.path.join(HERE, "..", "capture"))
OUT_DIR = os.path.join(CAPTURE, "parsed")

URL_RE = re.compile(rb"^\[S\] (https?://[^\s]+)")
TS_RE = re.compile(rb"[?&]ts=(\d+)")

def scan_one(path):
    """返回 {endpoint: [(line_no, url_str, ts)]}"""
    hits = defaultdict(list)
    try:
        with open(path, "rb") as f:
            for no, raw in enumerate(f, 1):
                m = URL_RE.match(raw)
                if not m:
                    continue
                try:
                    url = m.group(1).decode("utf-8", "ignore")
                except Exception:
                    continue
                # endpoint = scheme://host/path（去掉 query）
                ep = re.sub(r"\?.*$", "", url)
                tm = TS_RE.search(raw)
                ts = tm.group(1).decode() if tm else ""
                hits[ep].append((no, url, ts))
    except FileNotFoundError:
        print(f"[skip] 不存在: {path}")
    return hits

def main(files):
    os.makedirs(OUT_DIR, exist_ok=True)
    combined = defaultdict(list)  # endpoint -> [{file, line, ts, url}]
    per_file = {}
    for path in files:
        name = os.path.basename(path)
        hits = scan_one(path)
        per_file[name] = {ep: len(v) for ep, v in hits.items()}
        for ep, rows in hits.items():
            for no, url, ts in rows:
                combined[ep].append({"file": name, "line": no, "ts": ts, "url": url})

    # 汇总 JSON
    out_json = os.path.join(OUT_DIR, "urls_by_endpoint.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"per_file": per_file, "by_endpoint": combined}, f, ensure_ascii=False, indent=1)

    # INDEX.md
    lines = ["# 捕获日志索引（自动生成）", "",
             "> 由 `parse_session_logs.py` 生成。每条 [S] 记录 = 一个请求 URL 快照。",
             "> 详细参数/headers 请按 文件:行号 回原始日志查（[S] 行后紧跟 [SH-HEX]/[SH]）。", ""]
    for ep in sorted(combined):
        rows = combined[ep]
        # 按文件聚合行号
        by_file = defaultdict(list)
        for r in rows:
            by_file[r["file"]].append(r["line"])
        refs = "; ".join(f"{f}:{','.join(map(str, sorted(v)))}" for f, v in sorted(by_file.items()))
        lines.append(f"- `{ep}` ×{len(rows)}")
        lines.append(f"  - {refs}")
        lines.append("")
    with open(os.path.join(OUT_DIR, "INDEX.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[ok] {len(combined)} 个 endpoint，输出:")
    print(f"  {out_json}")
    print(f"  {os.path.join(OUT_DIR, 'INDEX.md')}")

if __name__ == "__main__":
    if len(__import__("sys").argv) < 2:
        print(__doc__)
    else:
        main(__import__("sys").argv[1:])

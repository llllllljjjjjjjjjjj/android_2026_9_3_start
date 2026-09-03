# -*- coding: utf-8 -*-
# comment_replay.py — 抖音评论接口 oracle 重放 + 翻页采集（最终版）
#
# 原理（2026-08-27 实证）：
#   1. 模板：POST /aweme/v2/comment/list/ 真实请求（capture/comment_paging_raw.json，
#      或 --from-charles 从 Charles 抓最新一条）
#   2. body 必须原样不动——服务器把 session_show_cids 与客户端会话状态绑定校验，
#      任何修改（真假 cid 都试过）→ -99999；zstd 重压缩同语义则无碍
#   3. 翻页只改 query 的 cursor（= 上页响应 cursor）+ oracle 重新签名
#   4. count 上限 ~50（服务器 cap ~48-50 条）；cursor 大步长可跳过重复带
#   5. 客户端按 cid 去重；某页 0 新 → cursor 额外 +80 跳过
#
# 用法：
#   python comment_replay.py                  # 默认：模板翻页采集（count=50，最多 20 页）
#   python comment_replay.py --from-charles   # 从 Charles 抓最新 list 请求做模板
#   python comment_replay.py --pages 30       # 翻 30 页
#   python comment_replay.py --out 我的评论.json
#   python comment_replay.py --single         # 只重放一次（不翻页）
#   python comment_replay.py --aweme-id <id>  # 换视频：砍视频专属参数，只换 aweme_id，cursor=0 起翻页
#   python comment_replay.py --cold <aweme_id>  # 实验：stream 首屏冷启动（当前 -99999 待解）
import argparse
import base64
import json
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

# 强制 IPv4：PC DNS 解析 api5-core-lf.amemv.com 到 IPv6（2409:...）时直连挂起
_orig_gai = socket.getaddrinfo
def _gai_v4(host, *a, **k):
    return [x for x in _orig_gai(host, *a, **k) if x[0] == socket.AF_INET] or _orig_gai(host, *a, **k)
socket.getaddrinfo = _gai_v4

import requests
import frida
import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]          # projects/dy
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
HOOK = ROOT / "hooks" / "dy_hook21.js"
TEMPLATE = ROOT / "capture" / "comment_paging_raw.json"
STREAM_TEMPLATE = ROOT / "capture" / "comment_stream_raw.json"
OUT_DEFAULT = ROOT / "capture" / "comments_out.json"

# oracle 输入基础头（签名引擎内部自洽；真实 app 调用 28065c 时 headers 输入含 x-ss-stub）
BASE_HDR = ("cookie\r\n"
            "passport_csrf_token=3f0e07710b4d5e6594f8249d3af55b4d; passport_csrf_token_default=3f0e07710b4d5e6594f8249d3af55b4d; "
            "store-region=cn-jx; store-region-src=did; "
            "odin_tt=1c90fbf9a6b7be2b015467ee8d21794b85b40a1eea84b9bb08538c17381cd640400d3eb0853772205a91f8690ec1cac245b1a9aeb5e96238d3859855c7bb4e5faff1c79ecb8fda5c6755583a92f5dea1; "
            "install_id=305014557150939; ttreq=1$acc983328eca331511c6dc5dd3f013547253a032\r\n"
            "user-agent\r\n"
            "com.ss.android.ugc.aweme/380001 (Linux; U; Android 10; zh_CN_#Hans; Pixel 4; Build/QQ3A.200605.001; "
            "Cronet/TTNetVersion:6f1e308d 2025-12-08 QuicVersion:21ac1950 2025-11-18)\r\n"
            "accept-encoding\r\ngzip, deflate, br")

_script = None


def oracle_connect():
    """attach 抖音进程，加载 dy_hook21.js RPC oracle。"""
    global _script
    subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"])
    pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
    dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
    _script = dev.attach(pid).create_script(open(HOOK, encoding="utf-8").read())
    _script.load()
    time.sleep(2)


def oracle_sign(url, stub):
    """返回八神头 dict（x-argus/x-gorgon/x-helios/x-khronos/x-ladon/x-medusa）。"""
    global _script
    if _script is None:
        oracle_connect()
    out = _script.exports_sync.oracle(url, BASE_HDR + "\r\nx-ss-stub\r\n" + stub)
    parts = out.split("\r\n")
    d = {}
    for i in range(0, len(parts) - 1, 2):
        d[parts[i]] = parts[i + 1]
    return d


def post(url, hdrs, body):
    """oracle 签名 → POST → 解析抖音响应（hex 前缀 + 尾部数据 → raw_decode）。"""
    h = dict(hdrs)
    for k in list(h):
        if k.lower() in ("x-argus", "x-gorgon", "x-helios", "x-khronos", "x-ladon", "x-medusa"):
            del h[k]
    h.update(oracle_sign(url, h.get("x-ss-stub", "")))
    h["x-ss-req-ticket"] = str(int(time.time() * 1000))
    h["activity_now_client"] = str(int(time.time() * 1000))
    h["accept-encoding"] = "gzip, deflate, br"      # 不声明 ttzip → 服务器回 br，requests 自动解
    h.pop("ttzip-version", None)
    r = requests.post(url, headers=h, data=body, timeout=25)
    raw = r.content
    s = raw.find(b"{")
    if s > 0:
        raw = raw[s:]
    return json.JSONDecoder().raw_decode(raw.decode("utf-8", errors="replace"))[0]


def load_entry(path):
    """.chlsj 条目 → (url, headers, body)。"""
    e = json.loads(Path(path).read_text(encoding="utf-8"))
    url = f"https://{e['host']}{e['path']}?{e['query']}"
    hdrs = {h["name"]: h["value"] for h in e["request"]["header"]["headers"] if not h["name"].startswith(":")}
    body = base64.b64decode(e["request"]["body"]["encoded"])
    return url, hdrs, body


# 实验 A 实证（2026-08-27）：list query 中这些视频专属参数全部可砍，oracle 照签、服务器照回
VIDEO_SPECIFIC_PARAMS = ("aweme_author", "authentication_token", "top_query_word", "common_flags",
                         "current_l1_comment_count", "comment_count", "is_fold_list")


def minimal_for_aweme(url0, aweme_id, cursor=0):
    """换视频：query 砍掉视频专属参数，只保留通用参数 + 新 aweme_id/cursor。"""
    from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit
    sp = urlsplit(url0)
    q = parse_qs(sp.query, keep_blank_values=True)
    kept = {k: v[0] for k, v in q.items() if k not in VIDEO_SPECIFIC_PARAMS}
    kept["aweme_id"] = aweme_id
    kept["cursor"] = str(cursor)
    return urlunsplit((sp.scheme, sp.netloc, sp.path, urlencode(kept), ""))


def from_charles():
    """从 Charles 会话抓最新一条 /aweme/v2/comment/list/ 请求做模板。"""
    sys.path.insert(0, str(ROOT.parents[1] / "android_mcp" / "servers" / "charles_mcp"))
    from charles_api import export_session
    entries = export_session()
    hits = [e for e in entries if (e.get("path") or "") == "/aweme/v2/comment/list/"]
    if not hits:
        raise SystemExit("Charles 会话中没有 /comment/list/ 请求，请先在抖音翻一页评论区")
    hit = max(hits, key=lambda e: e.get("times", {}).get("start", ""))
    url = f"https://{hit['host']}{hit['path']}?{hit['query']}"
    hdrs = {h["name"]: h["value"] for h in hit["request"]["header"]["headers"] if not h["name"].startswith(":")}
    body = base64.b64decode(hit["request"]["body"]["encoded"])
    print(f"[模板] Charles 最新请求 @ {hit.get('times', {}).get('start', '')[:19]}")
    return url, hdrs, body


def paging_loop(url0, hdrs0, body0, pages, count, out, check_id=None):
    """B 模式翻页：body 原样 + cursor 推进 + cid 去重。"""
    url0 = re.sub(r"(?<=count=)\d+", str(count), url0)
    seen = set()
    all_comments = []
    cursor = int(re.search(r"cursor=(\d+)", url0).group(1)) if re.search(r"cursor=(\d+)", url0) else 0
    dry_streak = 0
    for page in range(1, pages + 1):
        url = re.sub(r"(?<=cursor=)\d+", str(cursor), url0)
        j = post(url, hdrs0, body0)
        if j.get("status_code") != 0:
            print(f"[第{page}页 cursor={cursor}] status={j.get('status_code')} msg={j.get('status_msg')} — 停止")
            break
        cs = j.get("comments") or []
        if page == 1 and check_id and cs:
            c0 = cs[0]
            print(f"  [归属] 首条 aweme_id={c0.get('aweme_id')} 期望={check_id} 匹配={c0.get('aweme_id') == check_id} | {(c0.get('text') or '')[:30]}")
        new = [c for c in cs if c["cid"] not in seen]
        for c in cs:
            seen.add(c["cid"])
        all_comments.extend(new)
        nxt = j.get("cursor")
        print(f"[第{page}页 cursor={cursor}] 返回 {len(cs)} 条（新 {len(new)}）→ cursor={nxt} has_more={j.get('has_more')} | 累计 {len(all_comments)} 条")
        if not new:
            dry_streak += 1
            nxt = (nxt or cursor) + 80          # 重复带 → 大步长跳过
        else:
            dry_streak = 0
        if not j.get("has_more") or dry_streak >= 3:
            break
        cursor = nxt
        time.sleep(0.8)
    return all_comments


def cold_start(aweme_id, out):
    """实验模式：stream 首屏 → 构造 list 第一页（当前服务器对 cids 构造校验 -99999 待解）。"""
    d = zstd.ZstdDecompressor()
    c = zstd.ZstdCompressor()
    url_s, hdrs_s, body_s = load_entry(STREAM_TEMPLATE)
    j0 = post(url_s, hdrs_s, body_s)
    print(f"[冷启动] stream 首屏: status={j0.get('status_code')} comments={len(j0.get('comments') or [])} cursor={j0.get('cursor')}")
    if j0.get("status_code") != 0:
        return
    ccd = j0.get("comment_common_data")
    cids0 = [x["cid"] for x in (j0.get("comments") or [])]
    sid = re.search(r"session_id=([^&]+)", d.decompress(body_s).decode()).group(1)
    url_l, hdrs_l, _ = load_entry(TEMPLATE)
    url1 = re.sub(r"(?<=aweme_id=)\d+", aweme_id, url_l)
    url1 = re.sub(r"(?<=cursor=)\d+", str(j0.get("cursor")), url1)
    url1 = re.sub(r"(?<=current_l1_comment_count=)\d+", str(len(cids0)), url1)
    k = int(oracle_sign(url1, hdrs_l.get("x-ss-stub", ""))["X-Khronos"])
    url1 = re.sub(r"(?<=_rticket=)\d+", str(k * 1000 + 2000), url1)
    url1 = re.sub(r"(?<=ts=)\d+", str(k + 1), url1)
    from urllib.parse import quote
    form = (f"comment_common_comment_data={quote(ccd or '', safe='')}"
            f"&session_id={sid}"
            f"&session_show_cids={'%2C'.join(cids0)}"
            f"&ai_cmt_exposure=0&language=zh-Hans")
    j1 = post(url1, hdrs_l, c.compress(form.encode()))
    print(f"[冷启动] list 第一页: status={j1.get('status_code')} comments={len(j1.get('comments') or [])}")
    return j1.get("comments") or []


def main():
    ap = argparse.ArgumentParser(description="抖音评论接口 oracle 重放 + 翻页采集")
    ap.add_argument("--from-charles", action="store_true", help="从 Charles 抓最新 list 请求做模板")
    ap.add_argument("--pages", type=int, default=20, help="翻页数上限（默认 20）")
    ap.add_argument("--count", type=int, default=50, help="每页条数（服务器上限 ~50，默认 50）")
    ap.add_argument("--out", default=str(OUT_DEFAULT), help="输出 JSON 路径")
    ap.add_argument("--single", action="store_true", help="只重放一次模板请求（不翻页）")
    ap.add_argument("--aweme-id", metavar="ID", help="换视频：query 砍视频专属参数，只换 aweme_id，cursor=0 起翻页")
    ap.add_argument("--cold", metavar="AWEME_ID", help="实验：stream 首屏冷启动（已知 -99999 待解）")
    args = ap.parse_args()

    if args.cold:
        comments = cold_start(args.cold, args.out)
        Path(args.out).write_text(json.dumps(comments, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    if args.aweme_id:
        url0, hdrs0, body0 = load_entry(TEMPLATE)
        url0 = minimal_for_aweme(url0, args.aweme_id)
        print(f"[模板] {TEMPLATE.name} → minimal 换视频 aweme_id={args.aweme_id}")
    elif args.from_charles:
        url0, hdrs0, body0 = from_charles()
    else:
        url0, hdrs0, body0 = load_entry(TEMPLATE)
        print(f"[模板] {TEMPLATE.name}")

    if args.single:
        j = post(url0, hdrs0, body0)
        print(f"[单次] status={j.get('status_code')} comments={len(j.get('comments') or [])} cursor={j.get('cursor')} has_more={j.get('has_more')}")
        return

    comments = paging_loop(url0, hdrs0, body0, args.pages, args.count, args.out, check_id=args.aweme_id)
    Path(args.out).write_text(json.dumps(comments, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n完成：共 {len(comments)} 条去重评论 → {args.out}")


if __name__ == "__main__":
    main()

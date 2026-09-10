# -*- coding: utf-8 -*-
"""根据 aid 获取评论

用法:
  python comment_pull.py <aid> [滚动次数]
  python comment_pull.py --from results_kayak.json 3

流程: 打开视频 → 等评论自动加载 → 不足则点「评论」按钮 → 滚动加载 → RPC 收集
"""
import sys, json, time, subprocess, os, re
import frida

HOST = "127.0.0.1:27042"
JS = r"D:\reserve_agent\android\projects\dy\hooks\hook_comments_rpc.js"
PKG = "com.ss.android.ugc.aweme"
ADB = r"D:\reserve_agent\android\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
SERIAL = "9C181EC3BF7E0D"
OUTDIR = r"D:\reserve_agent\android\projects\dy\capture"
# 评论面板内滚动（屏幕下半区向上滑）
CMT_SWIPE = ("540", "1900", "540", "900", "400")


def adb(*a, timeout=30):
    return subprocess.run([ADB, "-s", SERIAL] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="ignore", timeout=timeout)


def attach_script(retries=3):
    for i in range(retries):
        try:
            dev = frida.get_device_manager().add_remote_device(HOST)
            pid = (adb("shell", "pidof", PKG).stdout or "").strip().split()
            session = dev.attach(int(pid[0])) if pid else dev.attach(PKG)
            script = session.create_script(open(JS, encoding="utf-8").read())
            script.on("message", lambda m, d: None)
            script.load()
            time.sleep(0.6)
            return session, script
        except Exception as e:
            print(f"[!] attach {i+1}/{retries} failed: {e}")
            time.sleep(3 * (i + 1))
    return None, None


def find_node_center(desc=None):
    """定位评论入口中心坐标（容错：优先 comment_container，其次 content-desc 含「评论」）"""
    try:
        adb("shell", "rm", "-f", "/sdcard/ui.xml")
        adb("shell", "uiautomator", "dump", "/sdcard/ui.xml")
        xml = adb("shell", "cat", "/sdcard/ui.xml").stdout or ""
        nodes = re.findall(r"<node[^>]+>", xml)

        def center(node):
            m = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', node)
            if not m:
                return None
            x1, y1, x2, y2 = map(int, m.groups())
            if x2 > x1 and y2 > y1:
                return ((x1 + x2) // 2, (y1 + y2) // 2)
            return None

        # 1) 首选「评论N，按钮」这类可点按钮
        for n in nodes:
            if "评论" in n and 'clickable="true"' in n:
                c = center(n)
                if c:
                    return c
        # 2) 评论容器
        for n in nodes:
            if "comment_container" in n or "comment_layout" in n:
                c = center(n)
                if c:
                    return c
        # 3) resource-id 含 comment
        for n in nodes:
            if "comment" in n.lower():
                c = center(n)
                if c:
                    return c
    except Exception as e:
        print(f"[!] ui dump failed: {type(e).__name__} {e}")
    return None


def collect_one(script, aid, scrolls):
    """打开视频 → 触达评论区 → 滚动加载（数据从 CommentItemList.comments 读取）"""
    adb("shell", "am", "start", "-a", "android.intent.action.VIEW",
        "-d", f"snssdk1128://aweme/detail/{aid}")
    time.sleep(6)

    c = find_node_center("评论")
    if c:
        print(f"    tap 评论按钮 @ {c}")
        adb("shell", "input", "tap", str(c[0]), str(c[1]))
        time.sleep(3)
    else:
        print("    [!] 未找到评论按钮")

    prev = script.exports_sync.count()
    print(f"    after open: {prev} comments")
    for k in range(scrolls):
        adb("shell", "input", "swipe", *CMT_SWIPE)
        time.sleep(3)
        cur = script.exports_sync.count()
        print(f"    scroll {k+1}/{scrolls}: {cur} comments")
        if cur == prev and k >= 2:
            print("    no new comments, stop scrolling")
            break
        prev = cur
    return script.exports_sync.count()


# 评论区里的非内容标签（需跳过，避免被当成昵称/内容）
LABELS = {"作者赞过", "置顶", "作者", "朋友", "翻译", "已折叠", "热评", "广告",
          "善语结善缘，恶言伤人心", "回复", "分享", "收藏"}


def structure(texts):
    """把扁平文本流分组为评论。
    实测顺序：昵称 → [标签] → [· 属地] → 内容 → [展开N条回复] → [点赞数]
    结束条件：展开N条回复 / 该条已有昵称+内容后又来新文本
    """
    out, cur = [], None

    def flush():
        nonlocal cur
        if cur and cur.get("nickname"):
            out.append(cur)
        cur = None

    for raw in texts:
        t = (raw or "").strip()
        if not t or t in LABELS:
            continue
        # 展开N条回复 → 本条结束
        m = re.match(r"^展开(\d+)条回复$", t)
        if m:
            if cur:
                cur["replyCount"] = int(m.group(1))
            flush()
            continue
        # IP 属地（评论中间元素，不结束）
        if t.startswith("·"):
            if cur:
                cur["ip"] = t.lstrip("· ").strip()
            continue
        # 纯数字 → 点赞数
        if re.match(r"^\d+(\.\d+)?[万wW]?$", t):
            if cur:
                cur["digg"] = t
            continue

        if cur is None:
            cur = {"nickname": t, "text": None, "ip": None, "replyCount": None, "digg": None}
        elif cur.get("text") is None:
            cur["text"] = t
        else:
            # 已有昵称+内容 → 上一条结束，本行为新昵称
            flush()
            cur = {"nickname": t, "text": None, "ip": None, "replyCount": None, "digg": None}
    flush()
    return out


def main():
    args = sys.argv[1:]
    scrolls = 3
    aids = []
    if args and args[0] == "--from":
        src = os.path.join(OUTDIR, args[1])
        n = int(args[2]) if len(args) > 2 else 3
        data = json.load(open(src, encoding="utf-8"))
        aids = [c["aid"] for c in data[:n] if c.get("aid")]
        if len(args) > 3:
            scrolls = int(args[3])
    else:
        if not args:
            print("usage: comment_pull.py <aid> [scrolls] | --from <results_x.json> [n] [scrolls]")
            return 1
        aids = [args[0]]
        if len(args) > 1:
            scrolls = int(args[1])

    session, script = attach_script()
    if not session:
        print("[!] abort: cannot attach")
        return 1
    try:
        script.exports_sync.clear()
        for i, aid in enumerate(aids, 1):
            print(f"[*] {i}/{len(aids)} aid={aid}")
            collect_one(script, aid, scrolls)
            if i < len(aids):
                adb("shell", "input", "keyevent", "4")
                time.sleep(2)

        data = script.exports_sync.getlist()
        out = os.path.join(OUTDIR, f"comments_{aids[0]}.json")
        json.dump({"aid": aids[0], "count": len(data), "comments": data},
                  open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"[*] comments: {len(data)} -> {out}")
        for c in data[:12]:
            rc = f"[回复{c['replyTotal']}]" if c.get("replyTotal") else ""
            tk = f" token={c.get('commentTokenLen')}" if c.get("commentTokenLen") else ""
            print(f"    cid={c.get('cid')} 赞{c.get('digg')} {rc} "
                  f"{c.get('nickname') or '-'}: {str(c.get('text') or '<加密>')[:36]}{tk}")
        return 0
    finally:
        try:
            session.detach()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())

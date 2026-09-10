# -*- coding: utf-8 -*-
"""按 aid 获取评论（纯 RPC 触发）：全部通过 Frida RPC 调用，不经 adb 触发/翻页

用法: python comment_rpc.py <aid> [滚动次数]
      python comment_rpc.py --from results_太阳.json 3 [滚动次数]
"""
import sys, json, time, os, subprocess
import frida
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import risk_health as rh

HOST = "127.0.0.1:27042"
JS = r"D:\reserve_agent\android\projects\dy\hooks\hook_comments_rpc.js"
PKG = "com.ss.android.ugc.aweme"
ADB = r"D:\reserve_agent\android\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
SERIAL = "9C181EC3BF7E0D"
OUTDIR = r"D:\reserve_agent\android\projects\dy\capture"


def adb(*a, timeout=30):
    """仅用于 attach 时取 pid"""
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


def collect_one(script, aid, scrolls, health):
    """纯 RPC：openurl 打开视频 → opencomments 点开评论区 → scroll 翻页"""
    r = script.exports_sync.openurl(f"snssdk1128://aweme/detail/{aid}")
    print(f"    RPC openurl({aid}) -> {r}")
    time.sleep(7)

    c = script.exports_sync.opencomments()
    print(f"    RPC opencomments -> {c}")
    time.sleep(4)
    print(f"    comments: {script.exports_sync.count()}")

    prev = script.exports_sync.count()
    for k in range(scrolls):
        n = script.exports_sync.scroll(0)
        time.sleep(3)
        cur = script.exports_sync.count()
        print(f"    scroll {k+1}/{scrolls}: rpc={n} comments={cur}")
        if cur == prev and k >= 2:
            print("    no new comments, stop")
            break
        prev = cur
    return script.exports_sync.count()


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
    elif args:
        aids = [args[0]]
        if len(args) > 1:
            scrolls = int(args[1])
    else:
        print("usage: comment_rpc.py <aid> [scrolls] | --from <results_x.json> [n] [scrolls]")
        return 1

    session, script = attach_script()
    if not session:
        print("[!] abort: cannot attach")
        return 1
    try:
        script.exports_sync.clear()
        health = rh.RiskHealth("comment")
        script.exports_sync.gohome()
        time.sleep(1.5)
        for i, aid in enumerate(aids, 1):
            print(f"[*] {i}/{len(aids)} aid={aid}")
            collect_one(script, aid, scrolls, health)
            if i < len(aids):
                script.exports_sync.gohome()
                time.sleep(2)

        # ★ 风控健康检查（依据 docs/flow-and-risk.md：评论链路要求前置 detail + 埋点配对）
        for u in (script.exports_sync.getpaths() or []):
            health.note(u)
        print()
        print(health.report())

        data = script.exports_sync.getlist()

        # ★ 降级判官
        if not data:
            verdict, detail = "soft", "未采集到评论（可能未点开评论区或已降级）"
        else:
            with_text = sum(1 for c in data if c.get("text"))
            if with_text == 0:
                verdict, detail = "soft", "评论条目无 text 字段"
            else:
                verdict, detail = "ok", "含完整评论字段"
        ok = rh.print_verdict(verdict, detail, len(data))

        out = os.path.join(OUTDIR, f"comments_{aids[0]}.json")
        json.dump({"aid": aids[0], "verdict": verdict, "count": len(data),
                   "riskHealth": health.report(), "comments": data},
                  open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"[*] comments: {len(data)} -> {out}")
        for c in data[:12]:
            rc = f"[回复{c['replyTotal']}]" if c.get("replyTotal") else ""
            print(f"    cid={c.get('cid')} 赞{c.get('digg')} {rc} "
                  f"{c.get('nickname') or '-'}: {str(c.get('text') or '')[:36]}")
        return 0 if ok else 2
    finally:
        try:
            session.detach()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())

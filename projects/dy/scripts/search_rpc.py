# -*- coding: utf-8 -*-
"""搜索（纯 RPC 触发）：全部通过 Frida RPC 调用 App 内部能力，不经 adb 触发

用法: python search_rpc.py <关键词> [页数] [间隔秒]
"""
import sys, json, time, os, urllib.parse
import frida
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import risk_health as rh

HOST = "127.0.0.1:27042"
JS = r"D:\reserve_agent\android\projects\dy\hooks\hook_searchcard_rpc.js"
PKG = "com.ss.android.ugc.aweme"
ADB = r"D:\reserve_agent\android\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
SERIAL = "9C181EC3BF7E0D"
OUTDIR = r"D:\reserve_agent\android\projects\dy\capture"

import subprocess


def adb(*a, timeout=30):
    """仅用于 attach 时取 pid（不参与触发/翻页）"""
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


def main():
    kw = sys.argv[1] if len(sys.argv) > 1 else "compass"
    pages = max(1, min(int(sys.argv[2]) if len(sys.argv) > 2 else 1, 10))
    delay = float(sys.argv[3]) if len(sys.argv) > 3 else 4.0

    session, script = attach_script()
    if not session:
        print("[!] abort: cannot attach")
        return 1
    try:
        script.exports_sync.clear()
        health = rh.RiskHealth("search")

        # 1) RPC 回桌面清场
        print(f"[*] RPC gohome -> {script.exports_sync.gohome()}")
        time.sleep(1.5)

        # 2) RPC 打开搜索（App 自身 Activity 上下文，无 adb）
        deep = f"snssdk1128://search?keyword={urllib.parse.quote(kw)}"
        r = script.exports_sync.openurl(deep)
        print(f"[*] RPC openurl({deep}) -> {r}")
        time.sleep(14)
        print(f"[*] after open: {script.exports_sync.count()} cards")

        # 3) RPC 滚动翻页（App 内 View 操作，无 adb input）
        for p in range(2, pages + 1):
            n = script.exports_sync.scroll(0)      # 0 = 自动按高度的 80%
            time.sleep(delay)
            print(f"[*] page {p}: scrolled={n} cards={script.exports_sync.count()}")

        # ★ 风控健康检查（依据 docs/flow-and-risk.md）
        for u in (script.exports_sync.getpaths() or []):
            health.note(u)
        print()
        print(health.report())

        cards = script.exports_sync.getcards()

        # ★ 降级判官：卡片数 == 0 或极少 → 疑似软降级
        if not cards:
            verdict, detail = "soft", "未采集到任何搜索结果卡片"
        else:
            # 检查卡片字段完整度（降级的数据常见字段缺失）
            with_desc = sum(1 for c in cards if c.get("desc"))
            if with_desc == 0:
                verdict, detail = "soft", "卡片无 desc 字段"
            else:
                verdict, detail = "ok", "含完整业务字段"
        ok = rh.print_verdict(verdict, detail, len(cards))

        out = os.path.join(OUTDIR, f"results_{kw}.json")
        json.dump({"keyword": kw, "verdict": verdict, "count": len(cards),
                   "riskHealth": health.report(), "cards": cards},
                  open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"[*] cards: {len(cards)} -> {out}")
        for c in cards[:8]:
            print(f"    {c.get('aid')} | {(c.get('desc') or '')[:44]} | 赞{c.get('digg')}")
        return 0 if ok else 2
    finally:
        try:
            session.detach()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())

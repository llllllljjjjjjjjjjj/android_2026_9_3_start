# -*- coding: utf-8 -*-
"""搜索接口打通（最终交付）：App 发请求 + RPC 取真实搜索结果（UTF-8 无损）

用法:
  python search_pull.py <keyword> [pages]
    pages: 翻页次数（每页滑动加载更多），默认 1，最大 10
"""
import sys, json, time, subprocess, os, urllib.parse
import frida

HOST = "127.0.0.1:27042"
JS = r"D:\reserve_agent\android\projects\dy\hooks\hook_searchcard_rpc.js"
PKG = "com.ss.android.ugc.aweme"
ADB = r"D:\reserve_agent\android\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
SERIAL = "9C181EC3BF7E0D"
OUTDIR = r"D:\reserve_agent\android\projects\dy\capture"
# 屏幕坐标（Pixel 4 1080x2280）
SWIPE = ("540", "1800", "540", "620", "400")


def adb(*a, timeout=30):
    """固定 UTF-8 解码，避免中文环境 GBK 崩溃"""
    return subprocess.run([ADB, "-s", SERIAL] + list(a),
                          capture_output=True, text=True,
                          encoding="utf-8", errors="ignore", timeout=timeout)


def adb_retry(*a, tries=3, timeout=30, backoff=2.0):
    """带重试的 adb（风控友好：失败退避，不暴力重试）"""
    last = None
    for i in range(tries):
        try:
            r = adb(*a, timeout=timeout)
            if r.returncode == 0:
                return r
            last = r
        except Exception as e:
            last = e
        if i < tries - 1:
            time.sleep(backoff * (i + 1))   # 线性退避
    print(f"[!] adb failed after {tries} tries: {a[:3]} ({last})")
    return last


def attach_script(retries=3):
    """连接 + 加载脚本，失败退避重试"""
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
            print(f"[!] attach attempt {i+1}/{retries} failed: {type(e).__name__} {e}")
            if i < retries - 1:
                time.sleep(3 * (i + 1))
    return None, None


def main():
    kw = sys.argv[1] if len(sys.argv) > 1 else "compass"
    pages = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    pages = max(1, min(pages, 10))
    delay = float(sys.argv[3]) if len(sys.argv) > 3 else 4.0   # 翻页间隔（拟真节奏）

    session, script = attach_script()
    if not session:
        print("[!] abort: cannot attach")
        return 1
    try:
        script.exports_sync.clear()

        print(f"[*] deeplink search: {kw} (pages={pages}, delay={delay}s)")
        # 1) 先回主页，清掉上一次搜索页（否则旧卡片会混入）
        adb_retry("shell", "input", "keyevent", "3")   # HOME
        time.sleep(1.5)
        # 2) 中文关键词必须 URL 编码，否则 am start 会失败/不触发
        deep = f"snssdk1128://search?keyword={urllib.parse.quote(kw)}"
        adb_retry("shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", deep)
        time.sleep(15)

        # 翻页：滑动加载更多（间隔可调，避免频控）
        for p in range(2, pages + 1):
            adb_retry("shell", "input", "swipe", *SWIPE)
            time.sleep(delay)
            print(f"[*] page {p}: cards so far = {script.exports_sync.count()}")

        cards = script.exports_sync.getcards()
        out = os.path.join(OUTDIR, f"results_{kw}.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(cards, f, ensure_ascii=False, indent=1)
        print(f"[*] cards: {len(cards)} -> {out}")
        for c in cards[:10]:
            print("   ", c.get("aid"), "|", (c.get("desc") or "")[:50], "| digg", c.get("digg"))
        return 0
    finally:
        try:
            session.detach()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())


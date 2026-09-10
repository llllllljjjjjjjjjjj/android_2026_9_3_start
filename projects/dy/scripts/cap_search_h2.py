# -*- coding: utf-8 -*-
"""对照实验 A: 禁用 QUIC 强制搜索走 TCP/HTTP2，抓搜索请求自身签名头
复用 cap_h2_headers.js(SSL_write HEADERS) + 搜索 deeplink
"""
import sys, time, subprocess, os, json

sys.path.insert(0, r"D:\reserve_agent\android\projects\dy\scripts")
import cap_h2_headers as ch2
import frida

HOST = "127.0.0.1:27042"
JS_H2 = r"D:\reserve_agent\android\projects\dy\hooks\cap_h2_headers.js"
JS_NOQUIC = r"D:\reserve_agent\android\projects\dy\hooks\no_quic.js"
PKG = "com.ss.android.ugc.aweme"
ADB = r"D:\reserve_agent\android\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
SERIAL = "9C181EC3BF7E0D"
OUTDIR = r"D:\reserve_agent\android\projects\dy\capture"
KW = sys.argv[1] if len(sys.argv) > 1 else "太阳"


def adb(*a, timeout=30):
    return subprocess.run([ADB, "-s", SERIAL] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="ignore", timeout=timeout)


def main():
    from urllib.parse import quote
    # 确保 App 运行
    pid = (adb("shell", "pidof", PKG).stdout or "").strip()
    if not pid:
        print("[*] 启动 App...")
        adb("shell", "am", "start", "-n", f"{PKG}/com.ss.android.ugc.aweme.main.MainActivity")
        time.sleep(10)
        pid = (adb("shell", "pidof", PKG).stdout or "").strip()
    print("[*] App pid:", pid)

    dev = frida.get_device_manager().add_remote_device(HOST)
    session = dev.attach(int(pid.split()[0]))
    frames = []

    def on_msg(m, data):
        if m.get("type") == "send" and data:
            frames.append((m.get("payload", {}), bytes(data)))

    sc_h2 = session.create_script(open(JS_H2, encoding="utf-8").read())
    sc_h2.on("message", on_msg)
    sc_h2.load()
    # 尝试禁用 QUIC（hook Cronet Builder）
    noquic = os.path.exists(JS_NOQUIC)
    if noquic:
        sc_nq = session.create_script(open(JS_NOQUIC, encoding="utf-8").read())
        sc_nq.load()
    print("[*] hooked SSL_write" + (" + no-quic" if noquic else ""))
    time.sleep(3)

    adb("shell", "input", "keyevent", "3")
    time.sleep(2)
    adb("shell", "am", "start", "-a", "android.intent.action.VIEW",
        "-d", "snssdk1128://search?keyword=%s" % quote(KW))
    print("[*] 触发搜索 deeplink, 采集 16s...")
    time.sleep(16)
    session.detach()
    print("[*] frames:", len(frames))

    def getk(h, k):
        for n, v in h:
            if n == k:
                return v
        return None

    allh = ch2.frames_to_headers(frames)
    print("[*] 全部 HEADERS path:")
    seen = set()
    for h in allh:
        p = (getk(h, ":path") or "?")
        base = p.split("?", 1)[0]
        if base not in seen:
            seen.add(base)
            print("    ", base[:80])

    # 找搜索请求 HEADERS
    target = next((h for h in allh if "search/general/stream" in (getk(h, ":path") or "")), None)
    if not target:
        print("[!] 搜索请求 HEADERS 未捕获（仍走 QUIC？）")
        return 1
    out = os.path.join(OUTDIR, "search_headers_search.json")
    json.dump({"headers": [[n, v] for n, v in target],
               "path": getk(target, ":path"), "authority": getk(target, ":authority")},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[*] 已保存 ->", out)
    for n, v in target:
        if n.lower() in ("x-argus", "x-gorgon", "x-khronos", "x-ss-stub", "x-ladon", "x-tt-token") or n in (":method", ":authority"):
            print("    %s: %s" % (n, str(v)[:70]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

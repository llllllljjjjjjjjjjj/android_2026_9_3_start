# -*- coding: utf-8 -*-
"""组合抓包: SSL_write HEADERS（含 x-ss-stub）+ RequestBuilder body，配对搜索请求
产出 capture/search_pair.json: {path, url, body, headers(native 层完整头)}
"""
import sys, time, subprocess, os, json

sys.path.insert(0, r"D:\reserve_agent\android\projects\dy\scripts")
import cap_h2_headers as ch2
import frida

HOST = "127.0.0.1:27042"
JS_H2 = r"D:\reserve_agent\android\projects\dy\hooks\cap_h2_headers.js"
JS_BODY = r"D:\reserve_agent\android\projects\dy\hooks\cap_search_body.js"
PKG = "com.ss.android.ugc.aweme"
ADB = r"D:\reserve_agent\android\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
SERIAL = "9C181EC3BF7E0D"
OUTDIR = r"D:\reserve_agent\android\projects\dy\capture"
KW = sys.argv[1] if len(sys.argv) > 1 else "compass"


def adb(*a, timeout=30):
    return subprocess.run([ADB, "-s", SERIAL] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="ignore", timeout=timeout)


def main():
    from urllib.parse import quote
    dev = frida.get_device_manager().add_remote_device(HOST)
    pid = (adb("shell", "pidof", PKG).stdout or "").strip().split()
    if not pid:
        print("[!] App 未运行")
        return 1
    session = dev.attach(int(pid[0]))

    frames = []

    def on_msg(m, data):
        if m.get("type") == "send" and data:
            frames.append((m.get("payload", {}), bytes(data)))

    sc_h2 = session.create_script(open(JS_H2, encoding="utf-8").read())
    sc_h2.on("message", on_msg)
    sc_h2.load()
    sc_body = session.create_script(open(JS_BODY, encoding="utf-8").read())
    sc_body.load()
    print("[*] hooked SSL_write + RequestBuilder, pid", pid[0])
    time.sleep(2)

    adb("shell", "input", "keyevent", "3")
    time.sleep(2)
    adb("shell", "am", "start", "-a", "android.intent.action.VIEW",
        "-d", "snssdk1128://search?keyword=%s" % quote(KW))
    print("[*] 已触发搜索 deeplink, 采集 14s...")
    time.sleep(14)
    cap = sc_body.exports_sync.get()   # detach 前先取 RPC 结果
    session.detach()

    print("[*] frames:", len(frames), "| search body cap:", "Y" if cap else "N")
    if not cap:
        print("[!] 未抓到搜索请求 body")
        return 1

    def getk(h, k):
        for n, v in h:
            if n == k:
                return v
        return None

    allh = ch2.frames_to_headers(frames)
    # 找与搜索 path 匹配的 HEADERS 组（含 x-ss-stub 的）
    target = None
    for h in allh:
        p = getk(h, ":path") or ""
        if "search/general/stream" in p and any(n == "x-ss-stub" for n, _ in h):
            target = h
            break
    if not target:
        # 退而求其次: 任意含 x-ss-stub 的组
        for h in allh:
            if any(n == "x-ss-stub" for n, _ in h):
                target = h
                break
    if not target:
        print("[!] 未抓到含 x-ss-stub 的 HEADERS")
        print("    paths:", sorted({(getk(h, ':path') or '?')[:70] for h in allh})[:10])
        return 1

    out = os.path.join(OUTDIR, "search_pair.json")
    json.dump({"path": getk(target, ":path"), "authority": getk(target, ":authority"),
               "headers": [[n, v] for n, v in target],
               "requestbuilder_url": cap.get("url"), "body": cap.get("body")},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[*] 已保存 ->", out)
    for n, v in target:
        if n in (":method", ":authority") or n.lower() in ("x-ss-stub", "x-argus", "x-gorgon", "x-khronos", "cookie", "content-length"):
            print("    %s: %s" % (n, str(v)[:90]))
    print("[*] body len:", len(cap.get("body") or ""))
    print("[*] body head:", (cap.get("body") or "")[:120])
    return 0


if __name__ == "__main__":
    sys.exit(main())

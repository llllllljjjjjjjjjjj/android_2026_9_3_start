# -*- coding: utf-8 -*-
"""轻量抓包: hook SSL_write -> 触发搜索 deeplink -> 抓新鲜签名头
复用 cap_h2_headers.py 的 HPACK/Huffman 解码函数；输出不覆盖原文件。
"""
import sys, time, subprocess, os, json

sys.path.insert(0, r"D:\reserve_agent\android\projects\dy\scripts")
import cap_h2_headers as ch2
import frida

HOST = "127.0.0.1:27042"
JS = r"D:\reserve_agent\android\projects\dy\hooks\cap_h2_headers.js"
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
    sc = session.create_script(open(JS, encoding="utf-8").read())
    frames = []

    def on_msg(m, data):
        if m.get("type") == "send" and data:
            frames.append((m.get("payload", {}), bytes(data)))

    sc.on("message", on_msg)
    sc.load()
    print("[*] hooked SSL_write, pid", pid[0])
    time.sleep(2)

    # 清场 + 触发搜索 deeplink
    adb("shell", "input", "keyevent", "3")
    time.sleep(2)
    adb("shell", "am", "start", "-a", "android.intent.action.VIEW",
        "-d", "snssdk1128://search?keyword=%s" % quote(KW))
    print("[*] 已触发搜索 deeplink, 采集 12s...")
    time.sleep(12)
    session.detach()
    print("[*] frames:", len(frames))

    allh = ch2.frames_to_headers(frames)

    def getk(h, k):
        for n, v in h:
            if n == k:
                return v
        return None

    def has_sig(h):
        for n, _ in h:
            if n and ("tt-token" in n.lower() or "ticket-guard" in n.lower()
                      or n.lower() == "x-argus" or n.lower() == "x-gorgon"):
                return True
        return False

    sig_groups = [h for h in allh if has_sig(h)]
    print("[*] header 组:", len(allh), "| 含签名头的组:", len(sig_groups))

    # 优先保存搜索接口的组，否则任意签名组
    search_groups = [h for h in sig_groups if "/search/" in (getk(h, ":path") or "")]
    target = (search_groups or sig_groups or [None])[0]
    if target:
        out = os.path.join(OUTDIR, "signature_headers_fresh.json")
        json.dump({"headers": [[n, v] for n, v in target],
                   "sourcePath": getk(target, ":path"),
                   "authority": getk(target, ":authority")},
                  open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("[*] 已保存 ->", out)
        print("[*] source:", str(getk(target, ":path"))[:80])
        for n, v in target:
            if n in (":method", ":authority", ":path") or n.lower() in (
                    "x-argus", "x-gorgon", "x-khronos", "x-ss-stub", "x-tt-token"):
                print("    %s: %s" % (n, str(v)[:70]))
        # 若含搜索 path，顺带输出其完整 headers 组数量
        return 0
    print("[!] 未抓到任何签名头组")
    for h in allh[:10]:
        print("     path:", str(getk(h, ":path"))[:80])
    return 1


if __name__ == "__main__":
    sys.exit(main())

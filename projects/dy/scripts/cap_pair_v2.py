# -*- coding: utf-8 -*-
"""组合抓包 v2: SSL_write HEADERS（含 x-ss-stub）+ RequestBuilder 全部 POST body
按 :path 配对 -> capture/pairs.json
"""
import sys, time, subprocess, os, json

sys.path.insert(0, r"D:\reserve_agent\android\projects\dy\scripts")
import cap_h2_headers as ch2
import frida

HOST = "127.0.0.1:27042"
JS_H2 = r"D:\reserve_agent\android\projects\dy\hooks\cap_h2_headers.js"
JS_BODY = r"D:\reserve_agent\android\projects\dy\hooks\cap_all_body.js"
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
    print("[*] hooked, pid", pid[0])
    time.sleep(2)

    adb("shell", "input", "keyevent", "3")
    time.sleep(2)
    adb("shell", "am", "start", "-a", "android.intent.action.VIEW",
        "-d", "snssdk1128://search?keyword=%s" % quote(KW))
    print("[*] 触发搜索, 采集 16s...")
    time.sleep(16)
    caps = sc_body.exports_sync.get()
    session.detach()

    print("[*] frames:", len(frames), "| POST bodies:", len(caps))

    def getk(h, k):
        for n, v in h:
            if n == k:
                return v
        return None

    allh = ch2.frames_to_headers(frames)
    # 按 path 前缀配对: headers(含 stub) + body
    pairs = []
    for h in allh:
        p = getk(h, ":path") or ""
        stub = None
        for n, v in h:
            if n == "x-ss-stub":
                stub = v
        if not stub:
            continue
        base = p.split("?", 1)[0]
        b = next((c for c in caps if (c.get("url") or "").split("?", 1)[0].endswith(base)), None)
        pairs.append({"path": base, "stub": stub, "body": (b or {}).get("body"),
                      "bodyLen": (b or {}).get("bodyLen"), "authority": getk(h, ":authority")})

    print("[*] stub+body 配对:", len(pairs))
    for p_ in pairs:
        print("   ", p_["path"], "stub=", p_["stub"], "bodyLen=", p_["bodyLen"])

    out = os.path.join(OUTDIR, "pairs.json")
    json.dump(pairs, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[*] 已保存 ->", out)
    # 打印所有 HEADERS path（诊断搜索是否被捕获）
    print("[*] 全部 HEADERS path:")
    for h in allh:
        print("    ", str(getk(h, ":path"))[:90])
    return 0


if __name__ == "__main__":
    sys.exit(main())

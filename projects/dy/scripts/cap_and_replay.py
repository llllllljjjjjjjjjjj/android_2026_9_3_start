# -*- coding: utf-8 -*-
"""组合抓搜索请求(HEADERS+body)并立即原样重放 —— 验证"搜索自身签名能否过 hit_shark"
前置: iptables/ip6tables 已阻断 UDP 443（QUIC 双栈），搜索回退 TCP 可被 SSL_write 捕获
"""
import sys, time, subprocess, os, json
sys.path.insert(0, r"D:\reserve_agent\android\projects\dy\scripts")
import cap_h2_headers as ch2
import search_pure as sp
import frida
from curl_cffi import requests as cr

HOST = "127.0.0.1:27042"
JS_H2 = r"D:\reserve_agent\android\projects\dy\hooks\cap_h2_headers.js"
JS_BODY = r"D:\reserve_agent\android\projects\dy\hooks\cap_all_body.js"
PKG = "com.ss.android.ugc.aweme"
ADB = r"D:\reserve_agent\android\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
SERIAL = "9C181EC3BF7E0D"
CAP = r"D:\reserve_agent\android\projects\dy\capture"
KW = sys.argv[1] if len(sys.argv) > 1 else "太阳"
IMPERSONATE = "chrome131_android"


def adb(*a, timeout=30):
    return subprocess.run([ADB, "-s", SERIAL] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="ignore", timeout=timeout)


def getk(h, k):
    for n, v in h:
        if n == k:
            return v
    return None


def main():
    from urllib.parse import quote
    pid = (adb("shell", "pidof", PKG).stdout or "").strip().split()
    if not pid:
        print("[!] App 未运行")
        return 1
    dev = frida.get_device_manager().add_remote_device(HOST)
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
    print("[*] 触发搜索, 采集 15s...")
    time.sleep(15)
    caps = sc_body.exports_sync.get()
    session.detach()

    allh = ch2.frames_to_headers(frames)
    search_h = next((h for h in allh if "search/general/stream" in (getk(h, ":path") or "")), None)
    search_b = next((c for c in caps if "search/general/stream" in (c.get("url") or "")), None)
    if not search_h:
        print("[!] 未抓到搜索 HEADERS（QUIC 阻断失效？）")
        return 1
    print("[*] 搜索 HEADERS OK, body cap:", "Y" if search_b else "N")
    if not search_b:
        print("[!] 未抓到搜索 body，无法配对重放")
        return 1

    # 保存配对
    pair = {"path": getk(search_h, ":path"), "authority": getk(search_h, ":authority"),
            "headers": [[n, v] for n, v in search_h], "body": search_b.get("body")}
    json.dump(pair, open(os.path.join(CAP, "search_full_pair.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # 校验 x-ss-stub = MD5(body)
    body = search_b["body"]
    stub_real = getk(search_h, "x-ss-stub")
    stub_calc = sp.compute_stub(body.encode("utf-8"))
    print(f"[*] x-ss-stub 抓包={stub_real} 计算={stub_calc} match={stub_real == stub_calc}")

    # 立即原样重放（headers + body 完全原样，仅 URL 用抓包 path）
    authority = getk(search_h, ":authority")
    path = getk(search_h, ":path")
    hdrs = {}
    for n, v in search_h:
        if n.startswith(":"):
            continue
        hdrs[n] = v
    url = f"https://{authority}{path}"
    print(f"[*] 原样重放 POST {authority} | body {len(body)}B | headers {len(hdrs)}")
    r = cr.post(url, data=body.encode("utf-8"), headers=hdrs, impersonate=IMPERSONATE, timeout=30)
    print(f"[*] HTTP {r.status_code} | {len(r.content)}B | CE={r.headers.get('content-encoding')}")
    ok, verdict, texts, data = sp.parse_response(r.content)
    print("[*] 判官:", verdict)
    items = sp.extract_items(data) if data else []
    print("[*] 条目:", len(items))
    for it in items[:5]:
        print("    aid=%s desc=%s" % (it.get("aweme_id"), str(it.get("desc"))[:50]))
    for t in texts[:2]:
        print("[*] 响应块:", t[:250])
    json.dump({"verdict": verdict, "items": items, "raw_head": r.content[:800].decode("utf-8", "ignore")},
              open(os.path.join(CAP, "replay_result.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())

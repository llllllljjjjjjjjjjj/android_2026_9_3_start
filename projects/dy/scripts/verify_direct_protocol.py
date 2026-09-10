# -*- coding: utf-8 -*-
"""协议直发验证（单脚本版）
1) 用 cap_request.js 捕获真实评论请求（URL + header + body）
2) 复用这些值直发：改 cursor 拉第二页
3) 判官：响应是否含真实评论（"cid"/"comments"）
"""
import sys, json, time, subprocess, os, urllib.request, gzip
from urllib.parse import urlparse, parse_qsl, urlencode
import frida

HOST = "127.0.0.1:27042"
JS = r"D:\reserve_agent\android\projects\dy\hooks\cap_request.js"
PKG = "com.ss.android.ugc.aweme"
ADB = r"D:\reserve_agent\android\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
SERIAL = "9C181EC3BF7E0D"
OUTDIR = r"D:\reserve_agent\android\projects\dy\capture"
AID = sys.argv[1] if len(sys.argv) > 1 else "7581630849533316401"
UA = ("com.ss.android.ugc.aweme/380001 (Linux; U; Android 10; zh_CN_#Hans; Pixel 4; "
      "Build/QQ3A.200605.001; Cronet/TTNetVersion:0fa322de 2024-11-06)")


def adb(*a, timeout=30):
    return subprocess.run([ADB, "-s", SERIAL] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="ignore", timeout=timeout)


def main():
    dev = frida.get_device_manager().add_remote_device(HOST)
    pid = (adb("shell", "pidof", PKG).stdout or "").strip().split()
    session = dev.attach(int(pid[0]))
    sc = session.create_script(open(JS, encoding="utf-8").read())
    sc.on("message", lambda m, d: None)
    sc.load()
    time.sleep(0.6)

    # 触发：adb 打开视频 + 点评论（触发本身就发真实请求）
    adb("shell", "am", "start", "-a", "android.intent.action.VIEW",
        "-d", f"snssdk1128://aweme/detail/{AID}")
    time.sleep(7)
    adb("shell", "input", "tap", "997", "1370")   # 评论按钮（动态定位另做）
    time.sleep(7)

    r = sc.exports_sync.get()
    if not r:
        print("[!] 未捕获评论请求")
        session.detach()
        return 1

    print(f"[*] 捕获 {r['method']} {r['path']}  headers={r['headerCount']} bodyLen={r['bodyLen']}")
    json.dump(r, open(os.path.join(OUTDIR, "comment_request_capture.json"), "w",
                      encoding="utf-8"), ensure_ascii=False, indent=1)

    url = r["url"]
    q = dict(parse_qsl(urlparse(url).query))
    print(f"[*] 参数数: {len(q)}")
    for k in ("aweme_id", "cursor", "count", "authentication_token", "comment_count", "aweme_author"):
        v = q.get(k)
        print(f"      {k} = {(str(v)[:50] + '...') if v and len(str(v)) > 50 else v}")
    print(f"[*] headers: {list((r.get('headers') or {}).keys())[:15]}")

    # 直发：cursor=20（第二页）
    q2 = dict(q)
    q2["cursor"] = "20"
    url2 = urlparse(url)._replace(query=urlencode(q2)).geturl()
    hdrs = {k: v for k, v in (r.get("headers") or {}).items()
            if isinstance(v, str) and not k.startswith("_")}
    hdrs.setdefault("User-Agent", UA)
    body = (r.get("body") or "").encode("utf-8")

    print(f"[*] 直发 cursor=20（headers={len(hdrs)}）")
    req = urllib.request.Request(url2, data=body if body else None,
                                 headers=hdrs, method=r.get("method") or "POST")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read()
            enc = resp.headers.get("Content-Encoding", "")
            if "gzip" in enc or raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            txt = raw.decode("utf-8", "ignore")
            print(f"[*] HTTP {resp.status} len={len(txt)}")
            print(f"[*] head: {txt[:260]}")
            has = '"cid"' in txt or '"comments"' in txt
            print(f"[*] ★ 含真实评论数据: {has}")
            open(os.path.join(OUTDIR, "comment_direct_response.txt"), "w",
                 encoding="utf-8").write(txt)
    except Exception as e:
        print(f"[!] 直发失败: {type(e).__name__} {e}")
        try:
            print("[!] resp:", e.read()[:400].decode("utf-8", "ignore"))
        except Exception:
            pass

    session.detach()
    return 0


if __name__ == "__main__":
    sys.exit(main())

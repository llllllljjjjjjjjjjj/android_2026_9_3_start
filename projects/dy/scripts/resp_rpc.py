# -*- coding: utf-8 -*-
"""A 方案调用器：App 自己发搜索请求（参数全由 App 生成），RPC 取回真实响应

用法:
  python resp_rpc.py search <keyword>      # 触发搜索并保存响应
  python resp_rpc.py list                  # 列出缓存响应
  python resp_rpc.py get <index>           # 取指定响应全文
"""
import sys, json, time, subprocess, os
import frida

HOST = "127.0.0.1:27042"
JS = r"D:\reserve_agent\android\projects\dy\hooks\resp_oracle.js"
PKG = "com.ss.android.ugc.aweme"
ADB = r"D:\reserve_agent\android\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
SERIAL = "9C181EC3BF7E0D"
OUTDIR = r"D:\reserve_agent\android\projects\dy\capture"


def adb(*args, timeout=30):
    return subprocess.run([ADB, "-s", SERIAL] + list(args), capture_output=True, text=True, timeout=timeout)


def attach():
    dev = frida.get_device_manager().add_remote_device(HOST)
    pid = (adb("shell", "pidof", PKG).stdout or "").strip().split()
    if pid:
        return dev.attach(int(pid[0]))
    return dev.attach(PKG)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    session = attach()
    script = session.create_script(open(JS, encoding="utf-8").read())
    script.on("message", lambda m, d: None)
    script.load()
    time.sleep(0.5)

    if cmd == "search":
        kw = sys.argv[2] if len(sys.argv) > 2 else "sunrise"
        script.exports.clear()
        print(f"[*] deeplink search: {kw}")
        adb("shell", "am", "start", "-a", "android.intent.action.VIEW",
            "-d", f"snssdk1128://search?keyword={kw}")
        time.sleep(14)
        n = script.exports.count()
        print(f"[*] cached responses: {n}")
        saved = []
        for i in range(n):
            r = script.exports.get(i)
            if not r:
                continue
            p = os.path.join(OUTDIR, f"resp_{kw}_{i}_{r['t']}.json")
            with open(p, "w", encoding="utf-8") as f:
                f.write(r["body"])
            saved.append((p, r["len"]))
        for p, ln in saved:
            print(f"    saved {os.path.basename(p)} ({ln} B)")
        # 找含真实搜索卡片的
        idxs = script.exports.find("aweme_video")
        print(f"[*] responses containing aweme_video: {idxs}")
    elif cmd == "get":
        i = int(sys.argv[2]) if len(sys.argv) > 2 else -1
        r = script.exports.get(i)
        print(json.dumps(r, ensure_ascii=False)[:3000] if r else "null")
    else:
        print(json.dumps(script.exports.list(), ensure_ascii=False, indent=1)[:2000])

    session.detach()


if __name__ == "__main__":
    main()

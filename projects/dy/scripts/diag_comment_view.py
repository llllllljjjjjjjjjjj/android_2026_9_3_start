# -*- coding: utf-8 -*-
"""诊断：打开视频后 dump 评论相关 View 树"""
import sys, json, time, subprocess, os
import frida

HOST = "127.0.0.1:27042"
JS = r"D:\reserve_agent\android\projects\dy\hooks\diag_comment_view.js"
PKG = "com.ss.android.ugc.aweme"
ADB = r"D:\reserve_agent\android\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
SERIAL = "9C181EC3BF7E0D"
AID = sys.argv[1] if len(sys.argv) > 1 else "7581630849533316401"


def adb(*a, timeout=30):
    return subprocess.run([ADB, "-s", SERIAL] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="ignore", timeout=timeout)


dev = frida.get_device_manager().add_remote_device(HOST)
pid = (adb("shell", "pidof", PKG).stdout or "").strip().split()
session = dev.attach(int(pid[0]))
script = session.create_script(open(JS, encoding="utf-8").read())
script.on("message", lambda m, d: None)
script.load()
time.sleep(0.8)

adb("shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", f"snssdk1128://aweme/detail/{AID}")
time.sleep(8)

res = script.exports_sync.dump()
if res.get("ok"):
    print(f"activity={res.get('act')}  scanned={res.get('scanned')}  commentViews={res.get('count')}")
    for it in res.get("items", [])[:14]:
        i = it["info"]
        print(f"  path={it['path']}")
        print(f"    cls={i.get('cls')}")
        print(f"    idName={i.get('idName')} clickable={i.get('clickable')} vis={i.get('vis')}")
        print(f"    desc={i.get('desc')} bounds={i.get('bounds')}")
else:
    print("FAILED:", res)

json.dump(res, open(r"D:\reserve_agent\android\projects\dy\capture\comment_view_dump.json", "w",
                    encoding="utf-8"), ensure_ascii=False, indent=1)
session.detach()

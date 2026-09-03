# -*- coding: utf-8 -*-
# try_sslocal.py — 用短链解析出的 sslocal:// native 深链直接打开（绕过 H5 中转）
import subprocess
import sys
import time
import urllib.parse

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"


def resolve(code):
    """短链 -> 302 Location -> 提取 detail_schema"""
    r = subprocess.run(["curl.exe", "-s", "-I",
                        f"https://v.douyin.com/{code}/"],
                       capture_output=True, text=True)
    loc = ""
    for line in r.stdout.splitlines():
        if line.lower().startswith("location:"):
            loc = line.split(":", 1)[1].strip()
    # detail_schema 是 URL 参数，URL 编码的
    m = urllib.parse.parse_qs(urllib.parse.urlparse(loc).query).get("detail_schema", [""])[0]
    return urllib.parse.unquote(m)


code = "WulVH5sFMGk"
schema = resolve(code)
print("detail_schema:", schema[:200], "...", flush=True)
print("scheme:", schema.split(":")[0], flush=True)

# 用 sslocal:// 深链打开
subprocess.check_call([ADB, "shell", "am", "start", "-a",
                       "android.intent.action.VIEW", "-d", schema],
                      stdout=subprocess.DEVNULL)
time.sleep(15)

# 检查页面
subprocess.run([ADB, "shell", "uiautomator", "dump", "/sdcard/ui.xml"],
               capture_output=True, timeout=20)
xml = subprocess.check_output([ADB, "shell", "cat", "/sdcard/ui.xml"]).decode(errors="replace")
for k in ("奥马", "冰箱", "网络异常", "官方直营", "立即购买"):
    print("HIT" if k in xml else "MISS", k)
subprocess.check_call([ADB, "shell", "dumpsys", "window", "|", "grep", "mCurrentFocus"])

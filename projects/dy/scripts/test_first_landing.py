# -*- coding: utf-8 -*-
# test_first_landing.py — 验证 first_landing 绕过：连续两次短链，第二次是否正常
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"


def ui_has(k):
    subprocess.run([ADB, "shell", "uiautomator", "dump", "/sdcard/ui.xml"],
                   capture_output=True, timeout=20)
    xml = subprocess.check_output([ADB, "shell", "cat", "/sdcard/ui.xml"]).decode(errors="replace")
    return k in xml


def check(label):
    abnormal = ui_has("网络异常")
    has_goods = ui_has("奥马") or ui_has("立即购买") or ui_has("官方直营")
    print(f"{label}: 网络异常={abnormal}  商品加载={has_goods}", flush=True)
    return not abnormal and has_goods


# 冷启动
subprocess.check_call([ADB, "shell", "am", "force-stop", "com.ss.android.ugc.aweme"],
                      stdout=subprocess.DEVNULL)
time.sleep(2)
subprocess.check_call([ADB, "shell", "monkey", "-p", "com.ss.android.ugc.aweme", "1"],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("冷启动 40s...", flush=True)
time.sleep(40)

# 第一次短链（消费 first_landing）
subprocess.check_call([ADB, "shell", "am", "start", "-a",
                       "android.intent.action.VIEW", "-d",
                       "https://v.douyin.com/WulVH5sFMGk/"],
                      stdout=subprocess.DEVNULL)
time.sleep(15)
check("第 1 次短链")

# 第二次短链（first_landing 已消费）
subprocess.check_call([ADB, "shell", "am", "start", "-a",
                       "android.intent.action.VIEW", "-d",
                       "https://v.douyin.com/WulVH5sFMGk/"],
                      stdout=subprocess.DEVNULL)
time.sleep(15)
check("第 2 次短链")

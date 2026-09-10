# -*- coding: utf-8 -*-
"""诊断：点击评论按钮后 UI 是否出现评论区"""
import re, subprocess, time

ADB = r"D:\reserve_agent\android\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
SERIAL = "9C181EC3BF7E0D"
AID = "7657917544935046470"


def adb(*a, timeout=30):
    return subprocess.run([ADB, "-s", SERIAL] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="ignore", timeout=timeout)


def dump():
    adb("shell", "rm", "-f", "/sdcard/ui.xml")
    adb("shell", "uiautomator", "dump", "/sdcard/ui.xml")
    return adb("shell", "cat", "/sdcard/ui.xml").stdout or ""


adb("shell", "am", "start", "-a", "android.intent.action.VIEW",
    "-d", f"snssdk1128://aweme/detail/{AID}")
time.sleep(7)

xml = dump()
nodes = re.findall(r"<node[^>]+>", xml)
print(f"nodes: {len(nodes)}")

# 找评论按钮坐标
target = None
for n in nodes:
    if "评论" in n and 'clickable="true"' in n:
        m = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', n)
        if m:
            x1, y1, x2, y2 = map(int, m.groups())
            target = ((x1 + x2) // 2, (y1 + y2) // 2)
            print(f"comment button node: {n[:200]}")
            break
print("target:", target)

if target:
    adb("shell", "input", "tap", str(target[0]), str(target[1]))
    time.sleep(5)
    xml2 = dump()
    nodes2 = re.findall(r"<node[^>]+>", xml2)
    print(f"\nafter tap nodes: {len(nodes2)}")
    # 找评论相关文本节点
    hits = 0
    for n in nodes2:
        m = re.search(r'text="([^"]{1,60})"', n)
        rid = re.search(r'resource-id="([^"]*)"', n)
        if m and m.group(1).strip():
            t = m.group(1)
            if any(k in (rid.group(1) if rid else "") for k in ("comment", "reply")) or \
               len(t) > 8:
                hits += 1
                if hits <= 12:
                    print(f"  text={t[:50]}  rid={(rid.group(1) if rid else '')[:60]}")
    print(f"\n候选文本节点: {hits}")
    # 是否出现评论相关资源 id
    for key in ("comment_content", "comment_list", "reply", "暂无评论"):
        cnt = sum(1 for n in nodes2 if key in n)
        print(f"  '{key}' in nodes: {cnt}")

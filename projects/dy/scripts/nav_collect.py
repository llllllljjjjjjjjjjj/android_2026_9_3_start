# -*- coding: utf-8 -*-
# nav_collect.py — App 内搜索导航采集（绕外部唤入风控，全自动无手动）
# 流程：搜索关键词 → UI 定位商品卡 → tap 进详情 → dump → 提取资质图片
# 用法: python nav_collect.py --kw "奥马326L冰箱" --name aoma
import argparse
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
OUT = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture")

DUMP_SH = """#!/system/bin/sh
pid=$1
out=/data/local/tmp/nav.bin
: > $out
while read range perms offset rest; do
  case "$perms" in
    rw-p)
      s=${range%-*}; e=${range#*-}
      s=$(printf %d 0x$s); e=$(printf %d 0x$e); sz=$((e-s))
      if [ $sz -gt 65536 ]; then
        dd if=/proc/$pid/mem bs=4096 skip=$((s/4096)) count=$((sz/4096)) >> $out 2>/dev/null
      fi
      ;;
  esac
done < /proc/$pid/maps
chmod 644 $out
"""


def adb(*args):
    return subprocess.check_output([ADB, *args]).decode(errors="replace").strip()


def dump_ui():
    subprocess.run([ADB, "shell", "uiautomator", "dump", "/sdcard/ui.xml"],
                   capture_output=True, timeout=20)
    try:
        return subprocess.check_output([ADB, "shell", "cat", "/sdcard/ui.xml"]).decode(errors="replace")
    except Exception:
        return ""


def find_clickable(xml, kw):
    """找含关键词的可点击节点（商品卡）"""
    try:
        root = ET.fromstring(xml)
    except Exception:
        return None
    for node in root.iter("node"):
        if node.get("clickable") != "true":
            continue
        desc = node.get("content-desc") or ""
        txt = node.get("text") or ""
        if kw in desc or kw in txt:
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.get("bounds") or "")
            if m:
                l, t, r, b = map(int, m.groups())
                return (l + r) // 2, (t + b) // 2
    return None


def tap(x, y):
    subprocess.run([ADB, "shell", "input", "tap", str(x), str(y)], capture_output=True)


def dump():
    pid = int(adb("shell", "pidof", PKG).split()[0])
    sh = OUT / "nav.sh"
    with open(sh, "w", encoding="utf-8", newline="\n") as f:
        f.write(DUMP_SH)
    subprocess.check_call([ADB, "push", str(sh), "/data/local/tmp/nav.sh"],
                          stdout=subprocess.DEVNULL)
    subprocess.check_call([ADB, "shell", "su", "-c",
                           f"sh /data/local/tmp/nav.sh {pid}"], timeout=180)
    local = OUT / "nav.bin"
    subprocess.check_call([ADB, "pull", "/data/local/tmp/nav.bin", str(local)],
                          stdout=subprocess.DEVNULL)
    return local


def extract_imgs(data):
    pat = rb"https?://p\d+-item\.ecombdimg\.com/img/tos-cn-i-[0-9a-z]+/([0-9a-f]{32})~tplv-[a-z0-9]+-water:"
    return sorted({m.group(1).decode() for m in re.finditer(pat, data)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kw", required=True, help="搜索关键词")
    ap.add_argument("--name", default="item")
    args = ap.parse_args()

    # 冷启动 + 进搜索
    subprocess.check_call([ADB, "shell", "am", "force-stop", PKG], stdout=subprocess.DEVNULL)
    time.sleep(2)
    subprocess.check_call([ADB, "shell", "monkey", "-p", PKG, "1"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("冷启动 40s...", flush=True)
    time.sleep(40)

    # 打开搜索并输入关键词
    subprocess.check_call([ADB, "shell", "am", "start", "-a",
                           "android.intent.action.VIEW", "-d",
                           f"snssdk1128://search?keyword={args.kw}"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"搜索「{args.kw}」...", flush=True)
    time.sleep(6)
    # 点击第一个联想词整行（触发搜索，第一行 bounds 约 [0,204][1080,325]）
    subprocess.run([ADB, "shell", "input", "tap", "540", "264"], capture_output=True)
    time.sleep(12)

    # 切「商品」tab
    xml = dump_ui()
    pt_tab = find_clickable(xml, "商品")
    if pt_tab:
        print(f"切商品 tab @{pt_tab}", flush=True)
        tap(*pt_tab)
        time.sleep(8)

    # 找商品卡点击
    pt = None
    for _ in range(6):
        xml = dump_ui()
        pt = find_clickable(xml, args.kw[:4])
        if pt:
            break
        subprocess.run([ADB, "shell", "input", "swipe", "540", "1700", "540", "600", "400"],
                       capture_output=True)
        time.sleep(2)
    if not pt:
        print("未定位到商品卡，请检查关键词；改为 dump 当前页（可能没进详情）", flush=True)
    else:
        print(f"点击商品卡 @{pt}", flush=True)
        tap(*pt)
        time.sleep(15)

    local = dump()
    data = local.read_bytes()
    hashes = extract_imgs(data)
    print(f"资质图片：{len(hashes)} 张", flush=True)
    water = "5Lqu54Wn5YWs56S65LiT55So5aSN5Y2w5peg5pWI"
    imgdir = OUT / f"nav_{args.name}_imgs"
    imgdir.mkdir(exist_ok=True)
    for i, h in enumerate(hashes, 1):
        url = (f"http://p26-item.ecombdimg.com/img/tos-cn-i-6vegkygxbk/{h}"
               f"~tplv-5mmsx3fupr-water:{water}:686:970.jpeg")
        f = imgdir / f"{i:02d}_{h}.jpeg"
        r = subprocess.run(["curl.exe", "-s", "-o", str(f),
                            "-w", "%{http_code} %{size_download}", url],
                           capture_output=True, text=True)
        print(f"  [{i}/{len(hashes)}] {h}  {r.stdout.strip()}", flush=True)
    print(f"\n完成 -> {imgdir}", flush=True)


if __name__ == "__main__":
    main()

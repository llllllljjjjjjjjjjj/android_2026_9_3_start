# -*- coding: utf-8 -*-
# auto_collect.py — 全自动采集：短链打开 → 自动点资质详情 → dump → 提取图片+参数
# 用法: python auto_collect.py --code qMRp9t3rONQ --name 小天鹅
import argparse
import json
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
ROOT = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy")
OUT = ROOT / "capture"

DUMP_SH = """#!/system/bin/sh
pid=$1
out=/data/local/tmp/auto.bin
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
    xml = adb("shell", "cat", "/sdcard/ui.xml")
    return xml


def find_btn(xml, texts):
    try:
        root = ET.fromstring(xml)
    except Exception:
        return None
    for node in root.iter("node"):
        desc = node.get("content-desc") or ""
        txt = node.get("text") or ""
        for t in texts:
            if t in desc or t in txt:
                b = node.get("bounds")
                m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b or "")
                if m:
                    l, t_, r, b_ = map(int, m.groups())
                    return (l + r) // 2, (t_ + b_) // 2
    return None


def tap(x, y):
    subprocess.run([ADB, "shell", "input", "tap", str(x), str(y)], capture_output=True)


def swipe_up():
    subprocess.run([ADB, "shell", "input", "swipe", "540", "1700", "540", "600", "400"],
                   capture_output=True)


def auto_open_qualification():
    """自动滚动 + 点击资质入口（官方正品/官方品牌授权/资质）"""
    keys = ["官方正品", "官方品牌授权", "品牌官方授权", "资质详情", "资质"]
    for _ in range(6):
        xml = dump_ui()
        pt = find_btn(xml, keys)
        if pt:
            print(f"点击资质入口 @{pt}", flush=True)
            tap(*pt)
            time.sleep(3)
            return True
        swipe_up()
        time.sleep(2)
    return False


def dump():
    pid = int(adb("shell", "pidof", PKG).split()[0])
    sh = OUT / "auto_dump.sh"
    with open(sh, "w", encoding="utf-8", newline="\n") as f:
        f.write(DUMP_SH)
    subprocess.check_call([ADB, "push", str(sh), "/data/local/tmp/auto.sh"],
                          stdout=subprocess.DEVNULL)
    print("dump rw 段...", flush=True)
    subprocess.check_call([ADB, "shell", "su", "-c",
                           f"sh /data/local/tmp/auto.sh {pid}"], timeout=180)
    local = OUT / "auto.bin"
    subprocess.check_call([ADB, "pull", "/data/local/tmp/auto.bin", str(local)],
                          stdout=subprocess.DEVNULL)
    return local


def extract_imgs(data):
    pat = rb"https?://p\d+-item\.ecombdimg\.com/img/tos-cn-i-[0-9a-z]+/([0-9a-f]{32})~tplv-[a-z0-9]+-water:"
    return sorted({m.group(1).decode() for m in re.finditer(pat, data)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", required=True)
    ap.add_argument("--name", default="item")
    args = ap.parse_args()

    print("force-stop + 冷启动清缓存（约 40s）...", flush=True)
    subprocess.check_call([ADB, "shell", "am", "force-stop", PKG],
                          stdout=subprocess.DEVNULL)
    time.sleep(2)
    subprocess.check_call([ADB, "shell", "monkey", "-p", PKG, "1"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(40)

    print("打开详情页...", flush=True)
    subprocess.check_call([ADB, "shell", "am", "start", "-a",
                           "android.intent.action.VIEW", "-d", f"https://v.douyin.com/{args.code}/"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(25)  # 等 detail 响应加载（部分商品加载慢）

    local = dump()
    data = local.read_bytes()
    print("dump size:", len(data), flush=True)

    hashes = extract_imgs(data)
    if not hashes:
        # 部分商品资质数据懒加载，点「品牌官方直营」触发后重 dump
        print("首轮 0 张，点击「品牌官方直营」触发懒加载...", flush=True)
        for _ in range(6):
            xml = dump_ui()
            pt = find_btn(xml, ["品牌官方直营", "官方直营", "官方正品", "品牌官方授权", "资质"])
            if pt:
                tap(*pt)
                time.sleep(4)
                break
            swipe_up()
            time.sleep(2)
        time.sleep(5)
        local = dump()
        data = local.read_bytes()
        print("重 dump size:", len(data), flush=True)
        hashes = extract_imgs(data)
    print(f"资质图片：{len(hashes)} 张", flush=True)
    water = "5Lqu54Wn5YWs56S65LiT55So5aSN5Y2w5peg5pWI"
    imgdir = OUT / f"auto_{args.name}_imgs"
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

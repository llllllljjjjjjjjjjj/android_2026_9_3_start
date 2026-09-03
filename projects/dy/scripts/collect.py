# -*- coding: utf-8 -*-
# collect.py — 统一采集：短链解析 → 自动打开 → 异常检测 → 手动回退 → dump 提取资质图片
# 用法: python collect.py --code WulVH5sFMGk --name aoma
import argparse
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
OUT = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture")

DUMP_SH = """#!/system/bin/sh
pid=$1
out=/data/local/tmp/collect.bin
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


def resolve(code):
    r = subprocess.run(["curl.exe", "-s", "-I", f"https://v.douyin.com/{code}/"],
                       capture_output=True, text=True)
    loc = ""
    for line in r.stdout.splitlines():
        if line.lower().startswith("location:"):
            loc = line.split(":", 1)[1].strip()
    q = urllib.parse.parse_qs(urllib.parse.urlparse(loc).query)
    pid = q.get("id", [""])[0] or q.get("product_id", [""])[0]
    gd = q.get("goods_detail", [""])[0]
    title = ""
    try:
        title = urllib.parse.parse_qs(urllib.parse.unquote(gd)).get("title", [""])[0]
    except Exception:
        pass
    return pid, title


def dump_ui_text():
    subprocess.run([ADB, "shell", "uiautomator", "dump", "/sdcard/ui.xml"],
                   capture_output=True, timeout=20)
    try:
        return subprocess.check_output([ADB, "shell", "cat", "/sdcard/ui.xml"]).decode(errors="replace")
    except Exception:
        return ""


def page_abnormal():
    xml = dump_ui_text()
    return "网络异常" in xml or "请刷新" in xml


def dump():
    pid = int(adb("shell", "pidof", PKG).split()[0])
    sh = OUT / "collect.sh"
    with open(sh, "w", encoding="utf-8", newline="\n") as f:
        f.write(DUMP_SH)
    subprocess.check_call([ADB, "push", str(sh), "/data/local/tmp/collect.sh"],
                          stdout=subprocess.DEVNULL)
    subprocess.check_call([ADB, "shell", "su", "-c",
                           f"sh /data/local/tmp/collect.sh {pid}"], timeout=180)
    local = OUT / "collect.bin"
    subprocess.check_call([ADB, "pull", "/data/local/tmp/collect.bin", str(local)],
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

    pid, title = resolve(args.code)
    print(f"解析短链：product_id={pid}  标题={title}", flush=True)

    # 冷启动（清上一个商品缓存）
    print("冷启动清缓存（约 40s）...", flush=True)
    subprocess.check_call([ADB, "shell", "am", "force-stop", PKG], stdout=subprocess.DEVNULL)
    time.sleep(2)
    subprocess.check_call([ADB, "shell", "monkey", "-p", PKG, "1"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(40)

    # 自动短链打开 + 异常检测
    print("短链打开...", flush=True)
    subprocess.check_call([ADB, "shell", "am", "start", "-a",
                           "android.intent.action.VIEW", "-d", f"https://v.douyin.com/{args.code}/"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(18)

    if page_abnormal():
        print("\n>>> 短链走 H5 中转，detail 被拒（网络异常）。", flush=True)
        print(">>> 请手动在 App 内搜索商品并点进详情页，看到商品信息后按回车...\n", flush=True)
        input()
        time.sleep(3)

    local = dump()
    data = local.read_bytes()
    hashes = extract_imgs(data)
    print(f"资质图片：{len(hashes)} 张", flush=True)
    water = "5Lqu54Wn5YWs56S65LiT55So5aSN5Y2w5peg5pWI"
    imgdir = OUT / f"collect_{args.name}_imgs"
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

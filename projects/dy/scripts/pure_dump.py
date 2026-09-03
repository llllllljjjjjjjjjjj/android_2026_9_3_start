# -*- coding: utf-8 -*-
# pure_dump.py — 纯 dump（不带打开）：手动打开详情页后直接提取资质图片
# 用法: python pure_dump.py --name aoma
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
OUT = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture")

DUMP_SH = """#!/system/bin/sh
pid=$1
out=/data/local/tmp/pure.bin
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="item")
    args = ap.parse_args()

    pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
    sh = OUT / "pure.sh"
    with open(sh, "w", encoding="utf-8", newline="\n") as f:
        f.write(DUMP_SH)
    subprocess.check_call([ADB, "push", str(sh), "/data/local/tmp/pure.sh"],
                          stdout=subprocess.DEVNULL)
    print("dump...", flush=True)
    subprocess.check_call([ADB, "shell", "su", "-c",
                           f"sh /data/local/tmp/pure.sh {pid}"], timeout=180)
    local = OUT / "pure.bin"
    subprocess.check_call([ADB, "pull", "/data/local/tmp/pure.bin", str(local)],
                          stdout=subprocess.DEVNULL)
    data = local.read_bytes()
    print("dump size:", len(data), flush=True)

    pat = rb"https?://p\d+-item\.ecombdimg\.com/img/tos-cn-i-[0-9a-z]+/([0-9a-f]{32})~tplv-[a-z0-9]+-water:"
    hashes = sorted({m.group(1).decode() for m in re.finditer(pat, data)})
    print(f"资质图片：{len(hashes)} 张", flush=True)
    water = "5Lqu54Wn5YWs56S65LiT55So5aSN5Y2w5peg5pWI"
    imgdir = OUT / f"pure_{args.name}_imgs"
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

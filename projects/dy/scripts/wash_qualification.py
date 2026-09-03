# -*- coding: utf-8 -*-
# wash_qualification.py — 提取洗衣机资质详情图片（dump + 提取 + 过滤旧图 + 下载）
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
OUT_DIR = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\wash_auth_imgs")
OUT_DIR.mkdir(exist_ok=True)

# 溪木源旧资质图 hash（过滤掉）
OLD_HASHES = {
    "0f415bcfe656455cb715ad4fd07c617a",
    "21a1df5d420d48bea0a9c998c1a20282",
    "7c796d3c625242c48270c52ae764cc67",
    "93d75646201a4f1588ed4d0920c7b786",
    "b59eff2a6c814821aca8c3710026bec9",
    "e52d68cbfa794d2aa423484f2a7b13eb",
}

DUMP_SH = """#!/system/bin/sh
pid=$1
out=/data/local/tmp/washdump.bin
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


def dump():
    pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
    sh = OUT_DIR / "dump.sh"
    with open(sh, "w", encoding="utf-8", newline="\n") as f:
        f.write(DUMP_SH)
    subprocess.check_call([ADB, "push", str(sh), "/data/local/tmp/washdump.sh"],
                          stdout=subprocess.DEVNULL)
    print("dump rw segments...", flush=True)
    subprocess.check_call([ADB, "shell", "su", "-c",
                           f"sh /data/local/tmp/washdump.sh {pid}"], timeout=180)
    local = OUT_DIR / "washdump.bin"
    subprocess.check_call([ADB, "pull", "/data/local/tmp/washdump.bin", str(local)],
                          stdout=subprocess.DEVNULL)
    return local


def extract_hashes(data):
    pat = rb"https?://p\d+-item\.ecombdimg\.com/img/tos-cn-i-[0-9a-z]+/([0-9a-f]{32})~tplv-[a-z0-9]+-water:"
    hashes = set()
    for m in re.finditer(pat, data):
        hashes.add(m.group(1).decode())
    return hashes


def main():
    local = dump()
    data = local.read_bytes()
    print("dump size:", len(data), flush=True)

    hashes = extract_hashes(data)
    print(f"全部资质图 hash：{len(hashes)}", flush=True)
    new = sorted(hashes - OLD_HASHES)
    print(f"新商品资质图（过滤旧图后）：{len(new)}", flush=True)

    WATER = "5Lqu54Wn5YWs56S65LiT55So5aSN5Y2w5peg5pWI"
    for i, h in enumerate(new, 1):
        url = (f"http://p26-item.ecombdimg.com/img/tos-cn-i-6vegkygxbk/{h}"
               f"~tplv-5mmsx3fupr-water:{WATER}:686:970.jpeg")
        out = OUT_DIR / f"wash_{i:02d}_{h}.jpeg"
        r = subprocess.run(["curl.exe", "-s", "-o", str(out),
                            "-w", "%{http_code} %{size_download}", url],
                           capture_output=True, text=True)
        print(f"[{i}/{len(new)}] {h}  {r.stdout.strip()}", flush=True)

    print(f"\n-> {OUT_DIR}")


if __name__ == "__main__":
    main()

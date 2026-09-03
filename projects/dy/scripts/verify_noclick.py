# -*- coding: utf-8 -*-
# verify_noclick.py — 验证：打开详情页不点资质，hash 是否已在内存
import re
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
OUT = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture")

DUMP_SH = """#!/system/bin/sh
pid=$1
out=/data/local/tmp/noclick.bin
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

# 打开洗衣机详情页
subprocess.check_call([ADB, "shell", "am", "start", "-a",
                       "android.intent.action.VIEW", "-d",
                       "https://v.douyin.com/qMRp9t3rONQ/"],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("打开详情页，等 15s（不点击）...", flush=True)
time.sleep(15)

# dump
pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
sh = OUT / "noclick.sh"
with open(sh, "w", encoding="utf-8", newline="\n") as f:
    f.write(DUMP_SH)
subprocess.check_call([ADB, "push", str(sh), "/data/local/tmp/noclick.sh"],
                      stdout=subprocess.DEVNULL)
print("dump...", flush=True)
subprocess.check_call([ADB, "shell", "su", "-c",
                       f"sh /data/local/tmp/noclick.sh {pid}"], timeout=180)
local = OUT / "noclick.bin"
subprocess.check_call([ADB, "pull", "/data/local/tmp/noclick.bin", str(local)],
                      stdout=subprocess.DEVNULL)

data = local.read_bytes()
pat = rb"https?://p\d+-item\.ecombdimg\.com/img/tos-cn-i-[0-9a-z]+/([0-9a-f]{32})~tplv-[a-z0-9]+-water:"
hashes = sorted({m.group(1).decode() for m in re.finditer(pat, data)})
print(f"\n不点击状态下，内存资质图 hash：{len(hashes)} 个", flush=True)
for h in hashes:
    print("  ", h, flush=True)

# -*- coding: utf-8 -*-
# fast_urldump.py — 只 dump native heap(libc_malloc)，快速抓「官方品牌授权」接口 URL
# 用法：点「官方品牌授权」触发接口后立即运行（接口 URL 在 Cronet 层，短命）。
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
OUT_DIR = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture")

DUMP_SH = """#!/system/bin/sh
pid=$1
out=/data/local/tmp/fasturl.bin
: > $out
while read range perms offset rest; do
  case "$perms" in
    rw-p)
      case "$rest" in
        *libc_malloc*)
          s=${range%-*}; e=${range#*-}
          s=$(printf %d 0x$s); e=$(printf %d 0x$e); sz=$((e-s))
          dd if=/proc/$pid/mem bs=4096 skip=$((s/4096)) count=$((sz/4096)) >> $out 2>/dev/null
          ;;
      esac
      ;;
  esac
done < /proc/$pid/maps
chmod 644 $out
"""


def extract_urls(data):
    urls = set()
    # UTF-8
    for m in re.finditer(rb"https://", data):
        off, end = m.start(), m.start()
        while end < len(data):
            b = data[end]
            if b == 0 or b in b' "\'<>,;{}[]\\\n\r\t' or b < 32 or b > 126:
                break
            end += 1
        u = data[off:end].decode("ascii", errors="ignore")
        if len(u) > 15:
            urls.add(u)
    # UTF-16
    pat16 = b"h\x00t\x00t\x00p\x00s\x00:\x00/\x00/\x00"
    for m in re.finditer(re.escape(pat16), data):
        off, end = m.start(), m.start()
        while end + 1 < len(data):
            b1, b2 = data[end], data[end + 1]
            if b1 == 0 and b2 == 0:
                break
            if not (32 <= b1 < 127 and b2 == 0):
                break
            end += 2
        u = data[off:end].decode("utf-16-le", errors="ignore")
        if len(u) > 15:
            urls.add(u)
    return urls


def main():
    pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
    sh = OUT_DIR / "fasturl.sh"
    with open(sh, "w", encoding="utf-8", newline="\n") as f:
        f.write(DUMP_SH)
    subprocess.check_call([ADB, "push", str(sh), "/data/local/tmp/fasturl.sh"],
                          stdout=subprocess.DEVNULL)
    print("dump libc_malloc...", flush=True)
    subprocess.check_call([ADB, "shell", "su", "-c",
                           f"sh /data/local/tmp/fasturl.sh {pid}"], timeout=60)
    local = OUT_DIR / "fasturl.bin"
    subprocess.check_call([ADB, "pull", "/data/local/tmp/fasturl.bin", str(local)],
                          stdout=subprocess.DEVNULL)
    data = local.read_bytes()
    print("dump size:", len(data), flush=True)

    urls = extract_urls(data)
    print("total urls:", len(urls), flush=True)
    kw = re.compile(r"ecombdapi|ecombdimg|jinritemai|haohuo|bytednsdoc|douyinpic",
                    re.I)
    hits = sorted(u for u in urls if kw.search(u))
    print(f"电商 URL：{len(hits)}\n", flush=True)
    for u in hits:
        print(u[:250], flush=True)
    out = OUT_DIR / "auth_img_urls_fast.txt"
    out.write_text("\n".join(hits), encoding="utf-8")
    print(f"\n-> {out}", flush=True)


if __name__ == "__main__":
    main()

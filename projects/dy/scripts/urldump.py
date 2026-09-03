# -*- coding: utf-8 -*-
# urldump.py — 零注入 root dump，搜「官方品牌授权」触发的接口/图片 URL
# 用法：用户点开产品参数弹层并点「官方品牌授权」触发接口后运行本脚本。
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
out=/data/local/tmp/urldump.bin
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
    return subprocess.check_output([ADB, *args]).decode(errors="replace")


def dump():
    pid = int(adb("shell", "pidof", PKG).split()[0])
    sh = OUT_DIR / "urldump.sh"
    with open(sh, "w", encoding="utf-8", newline="\n") as f:
        f.write(DUMP_SH)
    subprocess.check_call([ADB, "push", str(sh), "/data/local/tmp/urldump.sh"],
                          stdout=subprocess.DEVNULL)
    subprocess.check_call([ADB, "shell", "su", "-c",
                           f"sh /data/local/tmp/urldump.sh {pid}"], timeout=180)
    local = OUT_DIR / "urldump.bin"
    subprocess.check_call([ADB, "pull", "/data/local/tmp/urldump.bin", str(local)],
                          stdout=subprocess.DEVNULL)
    return local


def extract_urls(data, encoding):
    """提取所有 https:// URL"""
    if encoding == "utf16":
        pat = b"h\x00t\x00t\x00p\x00s\x00:\x00/\x00/\x00"
        step = 2
    else:
        pat = b"https://"
        step = 1
    urls = set()
    for m in re.finditer(re.escape(pat), data):
        off = m.start()
        # 向后读，直到遇到非 URL 字符
        end = off
        while end < len(data):
            if encoding == "utf16":
                if end + 1 >= len(data):
                    break
                b1, b2 = data[end], data[end + 1]
                if b1 == 0 and b2 == 0:
                    break
                if not (32 <= b1 < 127 and b2 == 0):
                    break
                end += 2
            else:
                b = data[end]
                if b == 0 or b in b' "\'<>,;{}[]\\\n\r\t':
                    break
                if b > 126 or b < 32:
                    break
                end += 1
        chunk = data[off:end]
        if encoding == "utf16":
            url = chunk.decode("utf-16-le", errors="ignore")
        else:
            url = chunk.decode("ascii", errors="ignore")
        if len(url) > 12:
            urls.add(url)
    return urls


def main():
    print("dumping rw segments...", flush=True)
    local = dump()
    data = local.read_bytes()
    print("dump size:", len(data), flush=True)

    urls = set()
    urls |= extract_urls(data, "utf16")
    urls |= extract_urls(data, "utf8")
    print("total urls:", len(urls), flush=True)

    kw = re.compile(r"qualif|license|licence|auth|brand|jinritemai|haohuo|"
                    r"douyinpic|ecombdimg|bytednsdoc|ecombdapi|multipleLic", re.I)
    hits = sorted(u for u in urls if kw.search(u))
    print(f"授权/图片相关 URL：{len(hits)}\n", flush=True)
    for u in hits:
        print(u[:300], flush=True)

    out = OUT_DIR / "auth_img_urls.txt"
    out.write_text("\n".join(hits), encoding="utf-8")
    print(f"\n-> {out}", flush=True)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
# extract_nowater.py — 提取资质图片无水印版 + 删 dump
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
OUT = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture")


def main():
    pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
    sh = OUT / "nw.sh"
    sh.write_text("""#!/system/bin/sh
pid=$1
out=/data/local/tmp/nw.bin
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
""", encoding="utf-8", newline="\n")
    subprocess.check_call([ADB, "push", str(sh), "/data/local/tmp/nw.sh"],
                          stdout=subprocess.DEVNULL)
    print("dump...", flush=True)
    subprocess.check_call([ADB, "shell", "su", "-c",
                           f"sh /data/local/tmp/nw.sh {pid}"], timeout=180)
    local = OUT / "nw.bin"
    subprocess.check_call([ADB, "pull", "/data/local/tmp/nw.bin", str(local)],
                          stdout=subprocess.DEVNULL)
    data = local.read_bytes()
    print("dump size:", len(data), flush=True)

    # 只提取 water 水印资质图 hash
    pat = rb"https?://p\d+-item\.ecombdimg\.com/img/tos-cn-i-[0-9a-z]+/([0-9a-f]{32})~tplv-[a-z0-9]+-water:"
    hashes = sorted({m.group(1).decode() for m in re.finditer(pat, data)})
    print(f"资质图 hash：{len(hashes)} 个", flush=True)

    imgdir = OUT / "aoma_nowater"
    imgdir.mkdir(exist_ok=True)
    ok = 0
    for i, h in enumerate(hashes, 1):
        # 无水印版 = image 后缀（原图），已验证 200
        url = f"http://p26-item.ecombdimg.com/img/tos-cn-i-6vegkygxbk/{h}~tplv-5mmsx3fupr-image.jpeg"
        f = imgdir / f"{i:02d}_{h}.jpeg"
        r = subprocess.run(["curl.exe", "-s", "-o", str(f),
                            "-w", "%{http_code} %{size_download}", url],
                           capture_output=True, text=True)
        code = r.stdout.strip().split()[0]
        if code == "200":
            ok += 1
            print(f"[{i}/{len(hashes)}] {h} 无水印 200", flush=True)
        else:
            print(f"[{i}/{len(hashes)}] {h} FAIL {r.stdout.strip()}", flush=True)
    print(f"\n成功 {ok}/{len(hashes)} -> {imgdir}", flush=True)

    # 删 dump（本地 + 设备）
    local.unlink(missing_ok=True)
    sh.unlink(missing_ok=True)
    subprocess.run([ADB, "shell", "su", "-c",
                    "rm -f /data/local/tmp/nw.bin /data/local/tmp/nw.sh"],
                   capture_output=True)
    print("dump 已删除", flush=True)


if __name__ == "__main__":
    main()

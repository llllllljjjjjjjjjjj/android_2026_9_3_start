# -*- coding: utf-8 -*-
# memdump_param.py — 零注入 root 内存 dump，提取产品参数（property_name_all/value）
# 用户点开参数弹层后运行：dump App 可读写段 → 搜 UTF-8/UTF-16 锚点 → 提取参数。
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
ROOT = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy")
OUT_DIR = ROOT / "capture"


def adb(*args):
    return subprocess.check_output([ADB, *args]).decode(errors="replace")


def dump_segments(pid):
    sh = """#!/system/bin/sh
pid=$1
out=/data/local/tmp/dump.bin
lst=/data/local/tmp/dump.lst
: > $out
: > $lst
while read range perms offset rest; do
  case "$perms" in
    rw-p)
      s=${range%-*}; e=${range#*-}
      s=$(printf %d 0x$s); e=$(printf %d 0x$e); sz=$((e-s))
      if [ $sz -gt 65536 ]; then
        off=$(stat -c %s $out)
        dd if=/proc/$pid/mem bs=4096 skip=$((s/4096)) count=$((sz/4096)) >> $out 2>/dev/null
        echo "$s $e $off" >> $lst
      fi
      ;;
  esac
done < /proc/$pid/maps
chmod 644 $out $lst
"""
    local_sh = OUT_DIR / "dump_segments.sh"
    with open(local_sh, "w", encoding="utf-8", newline="\n") as f:
        f.write(sh)
    subprocess.check_call([ADB, "push", str(local_sh), "/data/local/tmp/dump.sh"],
                          stdout=subprocess.DEVNULL)
    subprocess.check_call([ADB, "shell", "su", "-c",
                           f"sh /data/local/tmp/dump.sh {pid}"], timeout=180)
    local = OUT_DIR / "memdump.bin"
    local_lst = OUT_DIR / "memdump.lst"
    subprocess.check_call([ADB, "pull", "/data/local/tmp/dump.bin", str(local)],
                          stdout=subprocess.DEVNULL)
    subprocess.check_call([ADB, "pull", "/data/local/tmp/dump.lst", str(local_lst)],
                          stdout=subprocess.DEVNULL)
    return local, local_lst


def clean(s):
    # 截断韩文/替换符等指针残留，保留中文、字母数字、常用符号
    s = re.split(r'[\uac00-\ud7af\ufffd]', s)[0]
    return re.sub(r'[^\u4e00-\u9fff0-9a-zA-Z/（）()%\-|]', '', s)


def search_and_extract(dump, lst):
    data = dump.read_bytes()
    print("dump size:", len(data), flush=True)
    keys_full = "适用人群,包装类型,品牌".encode("utf-16-le")
    vals_full = "普通人群,普通装,溪木源".encode("utf-16-le")
    km = re.search(re.escape(keys_full), data)
    vm = re.search(re.escape(vals_full), data)
    if not km or not vm:
        print("FAIL: 未找到产品参数完整串（确认已打开参数弹层）", flush=True)
        return None

    def read_u16(off, maxlen=8000):
        raw = data[off:off + maxlen]
        end = raw.find(b"\x00\x00")
        if end > 0:
            raw = raw[:end]
        return raw.decode("utf-16-le", errors="replace").rstrip("\x00")

    keys = read_u16(km.start())
    vals = read_u16(vm.start())
    kl = [clean(x) for x in keys.split(",")]
    vl = [clean(x) for x in vals.split(",")]
    kl = [x for x in kl if x]
    vl = [x for x in vl if x]
    n = min(len(kl), len(vl))
    return kl[:n], vl[:n]


def main():
    pid = int(adb("shell", "pidof", PKG).split()[0])
    print("pid", pid, "dumping rw segments...", flush=True)
    dump, lst = dump_segments(pid)
    print("dumped ->", dump, flush=True)
    result = search_and_extract(dump, lst)
    if not result:
        sys.exit(1)
    kl, vl = result
    import json
    pairs = [{"name": kl[i], "value": vl[i]} for i in range(len(kl))]
    out = OUT_DIR / "detail_param_memdump.json"
    out.write_text(json.dumps(
        {"params": {p["name"]: p["value"] for p in pairs},
         "params_ordered": pairs}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"-> {out}")
    print(f"产品参数（{len(pairs)} 项）:")
    for p in pairs:
        print(f"  {p['name']:<24} | {p['value']}")


if __name__ == "__main__":
    main()

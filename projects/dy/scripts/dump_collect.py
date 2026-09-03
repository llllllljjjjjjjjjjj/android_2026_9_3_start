# -*- coding: utf-8 -*-
# dump_collect.py — 零注入 dump 一条命令采集：产品参数 + 资质详情图片
# 用法:
#   python dump_collect.py --code c11KamCtyGw --name 溪木源
# 流程: 短链打开详情页 → 等用户点开产品参数+资质详情 → dump → 提取两类数据 → 下载图片
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import parse_qsl

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
ROOT = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy")
OUT = ROOT / "capture"

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


def open_detail(code):
    subprocess.check_call([ADB, "shell", "am", "start", "-a",
                           "android.intent.action.VIEW", "-d", f"https://v.douyin.com/{code}/"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def dump():
    pid = int(adb("shell", "pidof", PKG).split()[0])
    sh = OUT / "collect_dump.sh"
    with open(sh, "w", encoding="utf-8", newline="\n") as f:
        f.write(DUMP_SH)
    subprocess.check_call([ADB, "push", str(sh), "/data/local/tmp/collect.sh"],
                          stdout=subprocess.DEVNULL)
    print("dump rw 段...", flush=True)
    subprocess.check_call([ADB, "shell", "su", "-c",
                           f"sh /data/local/tmp/collect.sh {pid}"], timeout=180)
    local = OUT / "collect.bin"
    subprocess.check_call([ADB, "pull", "/data/local/tmp/collect.bin", str(local)],
                          stdout=subprocess.DEVNULL)
    return local


def clean(s):
    s = re.split(r'[\uac00-\ud7af\ufffd]', s)[0]
    return re.sub(r'[^\u4e00-\u9fff0-9a-zA-Z/（）()%\-|]', '', s)


def read_u16(data, off, maxlen=8000):
    raw = data[off:off + maxlen]
    end = raw.find(b"\x00\x00")
    if end > 0:
        raw = raw[:end]
    return raw.decode("utf-16-le", errors="replace").rstrip("\x00")


def extract_params(data, key_anchor, val_anchor):
    """产品参数：搜 UTF-16 完整键串/值串（锚点=键串/值串前几项，不同商品不同）"""
    km = re.search(re.escape(key_anchor.encode("utf-16-le")), data)
    vm = re.search(re.escape(val_anchor.encode("utf-16-le")), data)
    if not km or not vm:
        return None
    keys = read_u16(data, km.start())
    vals = read_u16(data, vm.start())
    kl = [clean(x) for x in keys.split(",")]
    vl = [clean(x) for x in vals.split(",")]
    kl = [x for x in kl if x]
    vl = [x for x in vl if x]
    n = min(len(kl), len(vl))
    return [{"name": kl[i], "value": vl[i]} for i in range(n)]


def extract_auth_imgs(data):
    """资质图片：water 水印 URL hash"""
    pat = rb"https?://p\d+-item\.ecombdimg\.com/img/tos-cn-i-[0-9a-z]+/([0-9a-f]{32})~tplv-[a-z0-9]+-water:"
    return sorted({m.group(1).decode() for m in re.finditer(pat, data)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", required=True)
    ap.add_argument("--name", default="")
    ap.add_argument("--param-keys", default="适用人群,包装类型,品牌",
                    help="产品参数键串锚点（前几项，逗号分隔；换商品类型时改）")
    ap.add_argument("--param-vals", default="普通人群,普通装,溪木源",
                    help="产品参数值串锚点（前几项）")
    args = ap.parse_args()

    print("打开详情页...", flush=True)
    open_detail(args.code)
    print("\n>>> 请在手机上：打开产品参数弹层 + 点开资质详情（看到证照图后）按回车继续...\n", flush=True)
    input()

    local = dump()
    data = local.read_bytes()
    print("dump size:", len(data), flush=True)

    # 产品参数
    params = extract_params(data, args.param_keys, args.param_vals)
    if params:
        out = OUT / f"collect_{args.name or 'item'}_params.json"
        out.write_text(json.dumps({"params": {p["name"]: p["value"] for p in params},
                                   "params_ordered": params},
                                  ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n产品参数（{len(params)} 项）-> {out}", flush=True)
        for p in params:
            print(f"  {p['name']:<24} | {p['value']}", flush=True)
    else:
        print("未提取到产品参数（锚点不匹配，换 --param-keys/--param-vals）", flush=True)

    # 资质图片
    hashes = extract_auth_imgs(data)
    print(f"\n资质图片：{len(hashes)} 张", flush=True)
    water = "5Lqu54Wn5YWs56S65LiT55So5aSN5Y2w5peg5pWI"
    imgdir = OUT / f"collect_{args.name or 'item'}_imgs"
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

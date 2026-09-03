# -*- coding: utf-8 -*-
# download_auth_imgs.py — 下载资质详情全部图片
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT_DIR = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\auth_imgs")
OUT_DIR.mkdir(exist_ok=True)

HASHES = [
    "0f415bcfe656455cb715ad4fd07c617a",
    "21a1df5d420d48bea0a9c998c1a20282",
    "7c796d3c625242c48270c52ae764cc67",
    "93d75646201a4f1588ed4d0920c7b786",
    "b59eff2a6c814821aca8c3710026bec9",
    "e52d68cbfa794d2aa423484f2a7b13eb",
]
WATER = "5Lqu54Wn5YWs56S65LiT55So5aSN5Y2w5peg5pWI"

for i, h in enumerate(HASHES, 1):
    url = (f"http://p26-item.ecombdimg.com/img/tos-cn-i-6vegkygxbk/{h}"
           f"~tplv-5mmsx3fupr-water:{WATER}:686:970.jpeg")
    out = OUT_DIR / f"auth_{i:02d}_{h}.jpeg"
    r = subprocess.run(["curl.exe", "-s", "-o", str(out), "-w", "%{http_code} %{size_download}",
                        url], capture_output=True, text=True)
    print(f"[{i}/6] {h}  {r.stdout.strip()}")
print(f"\n-> {OUT_DIR}")

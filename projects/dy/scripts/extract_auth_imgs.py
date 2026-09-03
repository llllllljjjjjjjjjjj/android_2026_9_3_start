# -*- coding: utf-8 -*-
# extract_auth_imgs.py — 提取资质详情弹窗的全部图片 URL + 下载
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BIN = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\urldump.bin")
OUT_DIR = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\auth_imgs")

data = BIN.read_bytes()

# 资质图片特征：~tplv-5mmsx3fupr-water:（水印公示图），尺寸 :686:970.jpeg
# 完整 URL 形如 http://pXX-item.ecombdimg.com/img/tos-cn-i-6vegkygxbk/<hash>~tplv-5mmsx3fupr-water:<b64>:686:970.jpeg
pat = rb"https?://p\d+-item\.ecombdimg\.com/img/tos-cn-i-[0-9a-z]+/[0-9a-f]{32}~tplv-[a-z0-9]+-water:[A-Za-z0-9+/=]+:\d+:\d+\.jpeg"

urls = set()
for m in re.finditer(pat, data):
    urls.add(m.group(0).decode("ascii"))

print(f"资质图片 URL（去重）：{len(urls)}\n")
for u in sorted(urls):
    # 提取 hash 便于命名
    h = re.search(r"/([0-9a-f]{32})~", u)
    print(f"  {h.group(1) if h else '?'}  {u[:160]}")

# 保存清单
lst = OUT_DIR.parent / "auth_all_imgs.txt"
lst.write_text("\n".join(sorted(urls)), encoding="utf-8")
print(f"\n-> {lst}")

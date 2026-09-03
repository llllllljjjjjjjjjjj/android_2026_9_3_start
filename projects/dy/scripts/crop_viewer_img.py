# -*- coding: utf-8 -*-
# crop_viewer_img.py — 从查看器截图中裁出资质图片本体（去黑边）
import sys

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SRC = r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\brand_qualification_shot.png"
DST = r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\brand_qualification.png"
img = Image.open(SRC).convert("RGB")
w, h = img.size
px = img.load()

# 扫描非黑（亮度>30）区域边界
minx, miny, maxx, maxy = w, h, -1, -1
for y in range(0, h, 2):
    for x in range(0, w, 2):
        r, g, b = px[x, y]
        if r + g + b > 60:
            if x < minx: minx = x
            if x > maxx: maxx = x
            if y < miny: miny = y
            if y > maxy: maxy = y
print("content bbox:", minx, miny, maxx, maxy)
crop = img.crop((minx, miny, maxx + 1, maxy + 1))
crop.save(DST)
print("saved", DST, crop.size)

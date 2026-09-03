# -*- coding: utf-8 -*-
# ocr_crop.py — 截屏裁剪指定区域放大后 OCR（精确定位小字行）
# 用法: python ocr_crop.py <输出名> <x1> <y1> <x2> <y2> [scale]
import subprocess
import sys
from pathlib import Path

import pytesseract
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
NAME = sys.argv[1]
x1, y1, x2, y2 = (int(v) for v in sys.argv[2:6])
SCALE = int(sys.argv[6]) if len(sys.argv) > 6 else 3
PNG = ROOT / "capture" / f"{NAME}_crop.png"
TXT = ROOT / "capture" / f"{NAME}_crop.txt"

subprocess.check_call([ADB, "shell", "screencap", "-p", "/sdcard/_ocr.png"])
subprocess.check_call([ADB, "pull", "/sdcard/_ocr.png", str(PNG)], stdout=subprocess.DEVNULL)
img = Image.open(PNG).crop((x1, y1, x2, y2))
img = img.resize((img.width * SCALE, img.height * SCALE), Image.LANCZOS)
data = pytesseract.image_to_data(img, lang="chi_sim+eng", output_type=pytesseract.Output.DICT)
lines = []
for i in range(len(data["text"])):
    t = data["text"][i].strip()
    if not t or int(data["conf"][i]) < 20:
        continue
    X, Y, W, H = (data["left"][i], data["top"][i], data["width"][i], data["height"][i])
    # 映射回原屏幕坐标
    ox, oy = x1 + X // SCALE, y1 + Y // SCALE
    cx, cy = ox + W // (2 * SCALE), oy + H // (2 * SCALE)
    lines.append(f"{t}\t[{ox},{oy}]->[{ox + W // SCALE},{oy + H // SCALE}]\tcenter={cx},{cy}")
TXT.write_text("\n".join(lines), encoding="utf-8")
print(f"crop OCR done: {len(lines)} tokens -> {TXT}")

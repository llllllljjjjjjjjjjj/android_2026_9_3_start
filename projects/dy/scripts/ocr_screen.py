# -*- coding: utf-8 -*-
# ocr_screen.py — 截图 + tesseract OCR 输出文本与坐标（盲操作辅助）
# 用法: python ocr_screen.py [输出名]   → 生成 capture/<name>.png + .txt
import subprocess
import sys
from pathlib import Path

import pytesseract
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
NAME = sys.argv[1] if len(sys.argv) > 1 else "ocr_latest"
PNG = ROOT / "capture" / f"{NAME}.png"
TXT = ROOT / "capture" / f"{NAME}.txt"

subprocess.check_call([ADB, "shell", "screencap", "-p", "/sdcard/_ocr.png"])
subprocess.check_call([ADB, "pull", "/sdcard/_ocr.png", str(PNG)], stdout=subprocess.DEVNULL)
img = Image.open(PNG)
data = pytesseract.image_to_data(img, lang="chi_sim+eng", output_type=pytesseract.Output.DICT)
lines = []
for i in range(len(data["text"])):
    t = data["text"][i].strip()
    if not t or int(data["conf"][i]) < 30:
        continue
    x, y, w, h = (data["left"][i], data["top"][i], data["width"][i], data["height"][i])
    cx, cy = x + w // 2, y + h // 2
    lines.append(f"{t}\t{x},{y},{x+w},{y+h}\tcenter={cx},{cy}")
TXT.write_text("\n".join(lines), encoding="utf-8")
print(f"OCR done: {len(lines)} tokens -> {TXT}")

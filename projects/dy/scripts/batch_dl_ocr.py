# -*- coding: utf-8 -*-
# batch_dl_ocr.py — 批量下载图片 URL 并 OCR，匹配查看器资质图特征
import concurrent.futures
import re
import subprocess
import sys
from pathlib import Path

import pytesseract
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[1]
CAP = ROOT / "capture"
DL = CAP / "dl_pics"
DL.mkdir(exist_ok=True)

URLS = [l.strip() for l in (CAP / "pics_baseline.txt").read_text(encoding="utf-8").splitlines() if l.strip()]

FEAT = re.compile(r"(enon|检验|报告|证书|备案|资质|合格|No\.|NO\.|MO|Wh)", re.I)

def fetch(i, u):
    try:
        name = f"{i:03d}_" + re.sub(r"[^\w.-]", "_", u[8:])[:80]
        out = DL / name
        if out.exists():
            return out
        r = subprocess.run(
            ["curl.exe", "-s", "-m", "20", "-A", "Mozilla/5.0", "-o", str(out), u],
            capture_output=True,
        )
        if out.stat().st_size < 3000:
            out.unlink(missing_ok=True)
            return None
        return out
    except Exception:
        return None

def ocr(f):
    try:
        img = Image.open(f)
        w, h = img.size
        if w < 100 or h < 100:
            return None
        txt = pytesseract.image_to_string(img, lang="chi_sim+eng")
        return txt
    except Exception:
        return None

results = []
with concurrent.futures.ThreadPoolExecutor(6) as ex:
    futs = {ex.submit(fetch, i, u): (i, u) for i, u in enumerate(URLS)}
    for fut in concurrent.futures.as_completed(futs):
        i, u = futs[fut]
        f = fut.result()
        if not f:
            continue
        t = ocr(f)
        if t:
            flag = "**HIT**" if FEAT.search(t) else ""
            line = f"{flag} [{i:03d}] {f.name} ({f.stat().st_size}B)"
            if flag:
                line += f"\n    URL: {u[:180]}\n    TEXT: {t[:220].replace(chr(10), ' / ')}"
            results.append(line)

print(f"downloaded/ocr: {len(results)} files")
hits = [r for r in results if r.startswith("**HIT**")]
print(f"hits: {len(hits)}")
for r in hits:
    print(r)
(CAP / "dl_ocr_report.txt").write_text("\n".join(results), encoding="utf-8")

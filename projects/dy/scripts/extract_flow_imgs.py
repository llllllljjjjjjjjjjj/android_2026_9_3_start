# -*- coding: utf-8 -*-
# extract_flow_imgs.py — mitmproxy addon: 导出图片响应到文件
from pathlib import Path

from mitmproxy import http

OUT = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\flow_imgs")
OUT.mkdir(exist_ok=True)
IMG_CT = {"image/webp", "image/jpeg", "image/png", "image/heic", "image/heif", "application/octet-stream"}
idx = {"n": 0}


def response(flow: http.HTTPFlow):
    ct = flow.response.headers.get("content-type", "")
    url = flow.request.pretty_url
    is_img = any(k in ct for k in ("image", "octet")) or any(
        ext in url.lower() for ext in (".webp", ".png", ".jpg", ".jpeg", ".heic", ".gif")
    )
    if not is_img:
        return
    body = flow.response.content
    if not body or len(body) < 2000:
        return
    idx["n"] += 1
    ext = "bin"
    if "webp" in ct or url.lower().endswith(".webp"):
        ext = "webp"
    elif "png" in ct or url.lower().endswith(".png"):
        ext = "png"
    elif "jpeg" in ct or "jpg" in ct or url.lower().endswith((".jpg", ".jpeg")):
        ext = "jpg"
    elif "heic" in ct or url.lower().endswith(".heic"):
        ext = "heic"
    fn = OUT / f"img_{idx['n']:03d}.{ext}"
    fn.write_bytes(body)
    print(f"SAVED {fn.name} {len(body)}B <- {url[:160]}", flush=True)

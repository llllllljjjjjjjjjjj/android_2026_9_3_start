# -*- coding: utf-8 -*-
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
s = open(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\b64_ctx_full.json", encoding="utf-8", errors="replace").read()

# 找所有图片 base64
for pat, name in [(r"/9j/[A-Za-z0-9+/=]{100,}", "JPEG"),
                  (r"iVBORw0KGgo[A-Za-z0-9+/=]{100,}", "PNG"),
                  (r"UklGR[A-Za-z0-9+/=]{100,}", "WEBP")]:
    ms = list(re.finditer(pat, s))
    print(name, len(ms))
    for m in ms:
        pre = s[: m.start()]
        fm = list(re.finditer(r'"([A-Za-z_][A-Za-z0-9_]*)":\s*"', pre))
        fname = fm[-1].group(1) if fm else "?"
        print(f"  @{m.start()} field={fname} len={m.end()-m.start()}")
        # 上下文 200 字符
        print("   ", pre[-250:].replace("\n", " ")[:250])

# 所有 URL
print("---- urls ----")
for u in set(re.findall(r'https?://[^"\s\\]{10,900}?\.(?:png|jpg|jpeg|webp|heic|gif)[^"\s\\]*', s)):
    print("  ", u[:200])

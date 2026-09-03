# -*- coding: utf-8 -*-
import base64
import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
raw = open(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\b64\b64_01_0x706c4a5f36.txt", encoding="utf-8", errors="replace").read()

# 定位所有 /9j/ 开头的 base64 字段
imgs = []
for m in re.finditer(r'/9j/[A-Za-z0-9+/=]{500,}', raw):
    imgs.append(m.group(0))
print("jpeg b64 fields:", len(imgs))
for i, b64 in enumerate(imgs):
    # 到首个非 base64 字符截断
    b64 = re.match(r'[A-Za-z0-9+/=]+', b64).group(0)
    # 补 padding
    b64 += "=" * ((4 - len(b64) % 4) % 4)
    try:
        data = base64.b64decode(b64)
    except Exception as e:
        print(i, "decode err", e)
        continue
    fn = rf"D:\reserve_agent\ish-portable-kit\projects\dy\capture\b64_imgs\jpeg_{i}.jpg"
    open(fn, "wb").write(data)
    print(f"saved {fn} {len(data)}B")

# 也找 context 字段名
for m in re.finditer(r'"(image[^"]*|pic[^"]*|photo[^"]*|qualif[^"]*|auth[^"]*)"\s*:\s*"/9j/', raw):
    print("field:", m.group(1))
# 通用：/9j/ 前 100 字符
i = raw.find('/9j/')
print("context:", raw[max(0, i - 300):i])

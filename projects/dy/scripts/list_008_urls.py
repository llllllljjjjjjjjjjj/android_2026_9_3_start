# -*- coding: utf-8 -*-
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
raw = open(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\memscan_json\json_008.txt", encoding="utf-8", errors="replace").read()
urls = re.findall(r"https?:\\?/\\?/[^\"\s\\]{10,700}?\.(?:png|jpg|jpeg|webp|heic|gif)[^\"\s\\]*", raw)
seen = set()
out = []
for u in urls:
    u = u.replace("\\/", "/")
    if u not in seen:
        seen.add(u)
        out.append(u)
print("total urls in json_008:", len(out))
for u in out:
    print(" ", u[:220])

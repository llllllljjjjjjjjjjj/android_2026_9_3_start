# -*- coding: utf-8 -*-
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BIN = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\urldump.bin")
data = BIN.read_bytes()

# 找 authUrl 和 cal_jsb_auth 的上下文
for pat in [b"authUrl", b"cal_jsb_auth", b"auth_url", b"authurl"]:
    hits = list(re.finditer(re.escape(pat), data))
    print(f"\n== {pat!r}: {len(hits)} hits")
    for m in hits[:3]:
        off = m.start()
        a = max(0, off - 100)
        b = min(len(data), off + 500)
        txt = data[a:b].decode("utf-8", errors="replace")
        txt = txt.replace("\n", " ").replace("\x00", " ")
        print(f"   @{off:#x}: {txt[:400]}")

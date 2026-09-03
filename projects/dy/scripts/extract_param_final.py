# -*- coding: utf-8 -*-
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BIN = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\memdump.bin")
OUT = Path(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\detail_param_memdump.json")

data = BIN.read_bytes()

keys_full = "适用人群,包装类型,品牌,注册人/备案人的名称"
vals_full = "普通人群,普通装,溪木源,诺德溯源（广州）生物科技有限公司"

km = re.search(re.escape(keys_full.encode("utf-16-le")), data)
vm = re.search(re.escape(vals_full.encode("utf-16-le")), data)
assert km and vm, "not found"

# 读完整 UTF-16 字符串（到 \0\0 结束，上限 4000 字节）
def read_u16(off, maxlen=8000):
    raw = data[off:off+maxlen]
    end = raw.find(b"\x00\x00")
    if end > 0:
        raw = raw[:end]
    return raw.decode("utf-16-le", errors="replace").rstrip("\x00")

keys = read_u16(km.start())
vals = read_u16(vm.start())

def clean(s):
    # 截断韩文/替换符等指针残留，保留中文、字母数字、常用符号
    s = re.split(r'[\uac00-\ud7af\ufffd]', s)[0]
    return re.sub(r'[^\u4e00-\u9fff0-9a-zA-Z/（）()%\-|]', '', s)

kl = [clean(x) for x in keys.split(",") if clean(x)]
vl = [clean(x) for x in vals.split(",") if clean(x)]
n = min(len(kl), len(vl))
pairs = [{"name": kl[i], "value": vl[i]} for i in range(n)]

result = {"params": {p["name"]: p["value"] for p in pairs},
          "params_ordered": pairs}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n-> {OUT}")
print(f"产品参数（{len(pairs)} 项）:")
for p in pairs:
    print(f"  {p['name']:<24} | {p['value']}")

# -*- coding: utf-8 -*-
"""解出 libmetasec_ml.so（八神 native）用于符号/常量 triage"""
import zipfile, os
apk = r"D:\reserve_agent\android\android_mcp\_work\device_apks\com.ss.android.ugc.aweme\base.apk"
out = r"D:\reserve_agent\android\projects\dy\so_analysis"
os.makedirs(out, exist_ok=True)
z = zipfile.ZipFile(apk)
names = [n for n in z.namelist() if "metasec" in n.lower() or "mobsec" in n.lower()]
print("candidates:", names)
for n in names:
    data = z.read(n)
    p = os.path.join(out, os.path.basename(n))
    with open(p, "wb") as f:
        f.write(data)
    print("wrote", os.path.basename(n), len(data))

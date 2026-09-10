# -*- coding: utf-8 -*-
import zipfile, os
apk = r"D:\reserve_agent\android\android_mcp\_work\device_apks\com.ss.android.ugc.aweme\base.apk"
out = r"D:\reserve_agent\android\projects\dy\so_analysis"
os.makedirs(out, exist_ok=True)
z = zipfile.ZipFile(apk)
need = ["lib/arm64-v8a/libttboringssl.so",
        "lib/arm64-v8a/libsscronet.so",
        "lib/arm64-v8a/libsscronet-wrapper.so",
        "lib/arm64-v8a/libsscronet-wrapper-helper.so"]
for n in need:
    try:
        data = z.read(n)
        p = os.path.join(out, os.path.basename(n))
        with open(p, "wb") as f:
            f.write(data)
        print("wrote", os.path.basename(n), len(data))
    except KeyError:
        print("MISSING", n)

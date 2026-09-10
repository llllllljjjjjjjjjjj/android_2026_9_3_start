# -*- coding: utf-8 -*-
"""窄 token 扫描: 单遍读所有 .java, 找签名/header 关键字符串出现位置。
命中 -> projects/dy/artifacts/token_hits.txt (每行 文件|token)
用法: python token_scan.py [sources_root]
"""
import os, sys, time

ROOT = sys.argv[1] if len(sys.argv) > 1 else r"projects\dy\decompiled\sources"
OUT = r"projects\dy\artifacts\token_hits.txt"
TOKENS = [
    "x-argus", "x_argus", "X-Argus", "X-argus",
    "x-ladon", "x_ladon", "X-Ladon",
    "x-gorgon", "x-gorgon", "X-Gorgon",
    "x-tt-token", "x-tt-",
    "X-Tt-Token", "X-TT-TOKEN",
    "argus", "ladon",
    "aweme/business", "api/2/feed", "/aweme/v1/",
    "install_id", "device_register", "service/2/device_register/",
    "mcc_mnc", "aid=", "ttnet",
]
BYTES = [t.encode("utf-8", "ignore") for t in TOKENS]

def scan():
    t0 = time.time()
    total = 0
    hits = []
    for dp, dn, fn in os.walk(ROOT):
        for f in fn:
            if not f.endswith(".java"):
                continue
            total += 1
            fp = os.path.join(dp, f)
            try:
                with open(fp, "rb") as fh:
                    data = fh.read()
            except Exception:
                continue
            found = [t for t, b in zip(TOKENS, BYTES) if b in data]
            if found:
                rel = os.path.relpath(fp, ROOT).replace("\\", "/")
                hits.append(rel + " | " + ",".join(found))
            if total % 50000 == 0:
                print(f"  {total} files, {len(hits)} hit-files ({time.time()-t0:.0f}s)", flush=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(hits))
    print(f"DONE: {total} files scanned, {len(hits)} hit-files, {time.time()-t0:.0f}s -> {OUT}", flush=True)

scan()

# -*- coding: utf-8 -*-
"""dy 静态定向扫描：单遍遍历 decompiled/sources, 按关键词分组收集命中。
输出 projects/dy/artifacts/static_scan.json
用法: python static_scan.py [sources_root] [out_json]
"""
import os, re, sys, json, time

ROOT = sys.argv[1] if len(sys.argv) > 1 else r"projects\dy\decompiled\sources"
OUT = sys.argv[2] if len(sys.argv) > 2 else r"projects\dy\artifacts\static_scan.json"

GROUPS = {
    "app_entry": [re.compile(rb"extends\s+Application\b"), re.compile(rb"class\s+\w*App\w*Impl\b")],
    "netstack": [re.compile(rb"TTNet|ttnet|CronetEngine|cronet|NetworkStack"),],
    "okhttp_retrofit": [re.compile(rb"@(?:GET|POST|PUT|DELETE|PATCH)\s*\("),],
    "signature": [re.compile(rb"x-argus|x_argus|X-Argus|argus"), re.compile(rb"x-ladon|x_ladon|lado?n"), re.compile(rb"gorgon|x-gorgon"), re.compile(rb"Signature|sign\b|sig\b"),],
    "crypto": [re.compile(rb"MessageDigest|Mac\.getInstance|Cipher\.getInstance|HmacSHA|AES|RSA/"),],
    "device_token": [re.compile(rb"device.?id|install.?id|udid|device_id|mcc_mnc"),],
    "native_load": [re.compile(rb"System\.loadLibrary|loadLibrary"),],
    "dexvmp_stub": [re.compile(rb"native\s+.*\(|dex2c|DexVmp"),],
}

def scan(path):
    hits = {k: [] for k in GROUPS}
    total = 0
    t0 = time.time()
    for dp, dn, fn in os.walk(path):
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
            rel = os.path.relpath(fp, path).replace("\\", "/")
            for gname, pats in GROUPS.items():
                if len(hits[gname]) >= 200:
                    continue
                for p in pats:
                    m = p.search(data)
                    if m:
                        hits[gname].append(rel)
                        break
            if total % 50000 == 0:
                print(f"  scanned {total} files ({time.time()-t0:.0f}s)", flush=True)
    hits["_meta"] = {"files_scanned": total, "seconds": round(time.time()-t0, 1)}
    return hits

if __name__ == "__main__":
    print("scanning", ROOT, flush=True)
    res = scan(ROOT)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    for k in GROUPS:
        print(f"[{k}] {len(res[k])} hits")
    print("done ->", OUT, f"({res['_meta']['seconds']}s)")

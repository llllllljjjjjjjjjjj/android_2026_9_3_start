# -*- coding: utf-8 -*-
"""用 python 快速生成全部 .java 相对路径清单 (os.walk O(n), 避开 PS 数组 += 陷阱)。"""
import os, time, sys

ROOT = r"projects\dy\decompiled\sources"
OUT = r"projects\dy\artifacts\all_java_files.txt"
t0 = time.time()
root_abs = os.path.abspath(ROOT)
lines = []
n = 0
for dp, dn, fn in os.walk(root_abs):
    for f in fn:
        if f.endswith(".java"):
            rel = os.path.relpath(os.path.join(dp, f), root_abs).replace("\\", "/")
            lines.append(rel)
            n += 1
    if n % 100000 == 0 and n:
        print(f"  {n} files ({time.time()-t0:.0f}s)", flush=True)
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
print(f"DONE: {n} files in {time.time()-t0:.0f}s -> {OUT}", flush=True)

import os, re

ROOT = r"D:\reserve_agent\ish-portable-kit\projects\ctrip\decompiled\sources"

# BaseSign entry points to locate the native implementation registration
needles = [
    "m66707i",          # register impl
    "C22725a",          # BaseSign class references
    "baseSign",         # log tag / comments
    "BaseSign",
    "m66709k",          # simpleSign
]

hits = {}
for cur, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in {"androidx", "kotlin", "kotlinx", "okhttp3", "okio", "org", "bolts", "butterknife", "javax", "net", "logcat", "android"}]
    for name in files:
        if not name.endswith(".java"):
            continue
        p = os.path.join(cur, name)
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                for i, line in enumerate(f, 1):
                    for nd in needles:
                        if nd in line:
                            hits.setdefault(nd, []).append((p.replace(ROOT, ""), i, line.strip()))
        except Exception:
            pass

for nd in needles:
    arr = hits.get(nd, [])
    print(f"\n########## {nd}: {len(arr)} hits ##########")
    for rel, ln, line in arr[:40]:
        print(f"  {rel}:{ln}: {line[:160]}")

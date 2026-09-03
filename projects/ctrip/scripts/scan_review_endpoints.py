import os, re, sys

ROOT = r"D:\reserve_agent\ish-portable-kit\projects\ctrip\decompiled\sources"

# patterns for review/comment endpoints
soa = re.compile(r"soa2/", re.I)
kw = re.compile(r"comment|review|dianping|点评|评论|evaluation|评价", re.I)
urlpat = re.compile(r"https?://[^\s\"'<>)]+|/restapi/soa2/\d+[^\s\"'<>)]*", re.I)

hits = []
nfiles = 0
for cur, dirs, files in os.walk(ROOT):
    # skip huge third-party dirs that are unlikely to hold business endpoints
    dirs[:] = [d for d in dirs if d not in {"androidx", "kotlin", "kotlinx", "okhttp3", "okio", "org", "bolts", "butterknife", "javax", "net", "logcat"}]
    for name in files:
        if not name.endswith(".java"):
            continue
        p = os.path.join(cur, name)
        nfiles += 1
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                for i, line in enumerate(f, 1):
                    if "soa2" in line and kw.search(line):
                        # extract url
                        m = urlpat.search(line)
                        u = m.group(0) if m else ""
                        hits.append((p.replace(ROOT, ""), i, line.strip(), u))
        except Exception:
            pass

print(f"scanned {nfiles} files; {len(hits)} hit lines\n")
seen = set()
for rel, ln, line, url in hits:
    key = url if url else line
    if key in seen:
        continue
    seen.add(key)
    print(f"{rel}:{ln}\n   {line}\n   URL> {url}\n")

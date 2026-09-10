# -*- coding: utf-8 -*-
import re
lines = open(r"projects\dy\artifacts\all_java_files.txt", encoding="utf-8").read().splitlines()

def hits(pattern, cap=12):
    p = re.compile(pattern)
    matched = [l for l in lines if p.search(l)]
    print(f"== {pattern} -> {len(matched)} total")
    for x in matched[:cap]:
        print("   ", x)

for pat in [r"[Dd]evice[Rr]egister", r"[Tt]tnet", r"[Cc]ronet", r"[Aa]rgus",
            r"[Gg]orgon", r"[Ll]adon", r"[Ss]ecurity[Cc]ore", r"x-?argus"]:
    hits(pat)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify-skills.py - Validate the .dsh/skills bundles (DSH-native skills).

Checks for every skill bundle:
  1. SKILL.md exists with valid YAML frontmatter (name, description, whenToUse)
  2. frontmatter name matches the bundle dir name

Usage: python android_mcp\\scripts\\verify-skills.py [skill-name]
"""
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DST = os.path.join(ROOT, ".dsh", "skills")


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    names = sorted(d for d in os.listdir(DST) if os.path.isdir(os.path.join(DST, d)))
    if only:
        names = [n for n in names if n == only]
    failed = 0
    for name in names:
        bundle = os.path.join(DST, name)
        md = os.path.join(bundle, "SKILL.md")
        issues = []
        if not os.path.exists(md):
            issues.append("SKILL.md missing")
        else:
            raw = open(md, encoding="utf-8").read()
            m = re.match(r"^---\r?\n(.*?)\r?\n---", raw, re.S)
            if not m:
                issues.append("no YAML frontmatter")
            else:
                fm = yaml.safe_load(m.group(1))
                if not isinstance(fm, dict):
                    issues.append("frontmatter not a mapping")
                else:
                    for key in ("name", "description", "whenToUse"):
                        if not fm.get(key):
                            issues.append(f"frontmatter missing {key}")
                    if fm.get("name") != name:
                        issues.append(f"name mismatch: {fm.get('name')!r}")
        status = "OK  " if not issues else "FAIL"
        print(f"[{status}] {name}" + (f"  -> {', '.join(issues)}" if issues else ""))
        failed += len(issues)
    print(f"\n{len(names)} skills checked, {failed} issue(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

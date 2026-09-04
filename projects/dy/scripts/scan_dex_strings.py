"""Scan extracted dex files for ASCII/UTF-8 byte patterns and dump short context windows.

Usage:
    python scan_dex_strings.py <dex_dir> <pattern> [pattern2 ...]
Prints: dex_file, pattern, offset(s), surrounding printable context.
"""
import os
import re
import sys


def printable(buf: bytes, start: int, span: int = 80) -> str:
    lo = max(0, start - 20)
    hi = min(len(buf), start + span)
    win = buf[lo:hi]
    return repr(win.decode("utf-8", "replace"))


def main() -> None:
    dex_dir, patterns = sys.argv[1], sys.argv[2:]
    if not patterns:
        raise SystemExit("usage: scan_dex_strings.py <dex_dir> <pattern> ...")
    dex_files = sorted(
        os.path.join(dex_dir, f)
        for f in os.listdir(dex_dir)
        if f.endswith(".dex")
    )
    for dex in dex_files:
        with open(dex, "rb") as fh:
            data = fh.read()
        for pat in patterns:
            key = pat.encode("utf-8", "replace")
            pos = 0
            found = 0
            while found < 8:
                pos = data.find(key, pos)
                if pos < 0:
                    break
                print(f"{os.path.basename(dex)}\t{pat}\t{pos}\t{printable(data, pos)}")
                found += 1
                pos += 1


if __name__ == "__main__":
    main()

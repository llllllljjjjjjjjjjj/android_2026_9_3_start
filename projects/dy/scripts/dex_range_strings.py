"""Dump printable UTF-8 runs from a byte range of a dex file (helpful for
inspecting string-table regions around known URL constants).

Usage:
    python dex_range_strings.py <dex_file> <start_offset> [length]
"""
import re
import sys

PRINTABLE = re.compile(rb"[\x20-\x7e\xc0-\xff][\x20-\x7e\xc0-\xff]{3,}")


def main() -> None:
    dex = sys.argv[1]
    start = int(sys.argv[2])
    length = int(sys.argv[3]) if len(sys.argv) > 3 else 8192
    with open(dex, "rb") as fh:
        fh.seek(start)
        buf = fh.read(length)
    for m in PRINTABLE.finditer(buf):
        raw = m.group().decode("utf-8", "replace")
        off = start + m.start()
        print(f"{off:#x}\t{raw}")


if __name__ == "__main__":
    main()

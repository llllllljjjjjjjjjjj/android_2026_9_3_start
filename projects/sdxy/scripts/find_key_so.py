#!/usr/bin/env python3
"""Locate IV '01234ABCDEF56789' in SO and dump surrounding bytes/strings to find AES key."""
import re
import sys

SO = r'projects\sdxy\so_analysis\libapp.so'


def dump_hex(data, off, n=64):
    return ' '.join(f'{b:02x}' for b in data[off:off + n])


def extract_strings(data, start, end, minlen=8):
    out = []
    cur = []
    for i in range(start, end):
        b = data[i]
        if 0x20 <= b <= 0x7e:
            cur.append(chr(b))
        else:
            if len(cur) >= minlen:
                out.append((i - len(cur), ''.join(cur)))
            cur = []
    if len(cur) >= minlen:
        out.append((end - len(cur), ''.join(cur)))
    return out


def main():
    with open(SO, 'rb') as f:
        data = f.read()
    print(f'[+] {SO} size={len(data)} (0x{len(data):x})')

    iv = b'01234ABCDEF56789'
    hits = [m.start() for m in re.finditer(re.escape(iv), data)]
    print(f'[+] IV occurrences: {len(hits)}')
    for off in hits:
        print(f'\n=== IV @ file offset 0x{off:x} (VA 0x{off:x} in flat file) ===')
        lo = max(0, off - 256)
        hi = min(len(data), off + 512)
        strs = extract_strings(data, lo, hi)
        print(f'    strings in [{lo:x},{hi:x}]:')
        for s_off, s in strs:
            print(f'      0x{s_off:x}: {s!r}')
        print(f'    hex around IV:')
        print(f'      {dump_hex(data, off - 32, 96)}')

    # Also look for 32-char printable strings near any run-front / api.huachenjie references
    print('\n[+] searching 32-byte printable candidates across whole file...')
    candidates = set()
    for m in re.finditer(rb'[A-Za-z0-9+/=_-]{32}', data):
        s = m.group().decode('latin1')
        # heuristic: contain both upper and digit, not pure dart symbol
        if re.search(r'[A-Z]', s) and re.search(r'[0-9]', s) and not s.startswith('_'):
            candidates.add(s)
    for s in sorted(candidates)[:200]:
        print(f'    {s}')


if __name__ == '__main__':
    main()

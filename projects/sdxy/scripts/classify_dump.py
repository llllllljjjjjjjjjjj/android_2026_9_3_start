#!/usr/bin/env python3
"""Classify dumped DEX: find business dex (contains com/huachenjie) and print class counts."""
import glob
import os
import struct

DUMP = r'projects\sdxy\apk\dump\sdxy_dump'


def dex_class_count(data):
    if data[:4] != b'dex\n':
        return -1
    return struct.unpack('<I', data[96:100])[0]


def main():
    files = sorted(glob.glob(os.path.join(DUMP, '*.dex')), key=os.path.getsize)
    print(f'[+] total dex files: {len(files)}')
    business = []
    for f in files:
        with open(f, 'rb') as fh:
            data = fh.read()
        size = len(data)
        cls = dex_class_count(data)
        hit = b'com/huachenjie' in data or b'Lcom/huachenjie' in data
        flags = []
        if hit:
            flags.append('BUSINESS')
        if b'com/netease/nis' in data:
            flags.append('nis-shell')
        if b'com/byted' in data or b'pangle' in data:
            flags.append('pangle')
        if b'com/kwad' in data:
            flags.append('kwad')
        if b'com/qq/e' in data or b'gdt' in data:
            flags.append('gdt')
        tag = ','.join(flags) if flags else '-'
        print(f'{os.path.basename(f):28s} size={size:>9d} classes={cls:>7d} {tag}')
        if hit:
            business.append((f, size, cls))
    print(f'\n[+] business dex candidates: {len(business)}')
    for f, size, cls in business:
        print(f'    {os.path.basename(f)} size={size} classes={cls}')


if __name__ == '__main__':
    main()

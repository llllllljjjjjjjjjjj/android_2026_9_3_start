#!/usr/bin/env python3
"""Scan base_new.vdex for embedded DEX files and analyze protection layout."""
import re
import struct
import sys

VDEX = r'projects\sdxy\apk\base_new.vdex'


def read_dex_header(data, off):
    """Parse DEX header at off, return dict or None."""
    if off + 0x70 > len(data):
        return None
    if data[off:off + 4] != b'dex\n':
        return None
    hdr = {}
    hdr['magic'] = data[off:off + 8]
    hdr['version'] = data[off + 4:off + 8].decode('latin1')
    hdr['checksum'] = struct.unpack('<I', data[off + 8:off + 12])[0]
    hdr['file_size'] = struct.unpack('<I', data[off + 32:off + 36])[0]
    hdr['header_size'] = struct.unpack('<I', data[off + 36:off + 40])[0]
    hdr['endian'] = struct.unpack('<I', data[off + 40:off + 44])[0]
    hdr['map_off'] = struct.unpack('<I', data[off + 52:off + 56])[0]
    hdr['class_defs_size'] = struct.unpack('<I', data[off + 96:off + 100])[0]
    hdr['class_defs_off'] = struct.unpack('<I', data[off + 100:off + 104])[0]
    hdr['method_ids_size'] = struct.unpack('<I', data[off + 88:off + 92])[0]
    return hdr


def main():
    with open(VDEX, 'rb') as f:
        data = f.read()
    print(f'[+] vdex size = {len(data)} (0x{len(data):x})')
    print(f'[+] vdex magic = {data[:8]!r}')
    if data[:4] == b'vdex':
        ver = data[4:8].decode('latin1', 'replace')
        print(f'[+] vdex version = {ver}')
        # vdex header: magic(4) version(4) num_dex_files(4) dex_size(4) ...
        n_dex = struct.unpack('<I', data[8:12])[0]
        dex_size = struct.unpack('<I', data[12:16])[0]
        print(f'[+] num_dex_files = {n_dex}, dex_size = {dex_size} (0x{dex_size:x})')

    # Scan for dex magic "dex\n"
    hits = [m.start() for m in re.finditer(b'dex\n', data)]
    print(f'[+] "dex\\n" occurrences = {len(hits)}')
    valid = []
    for off in hits:
        hdr = read_dex_header(data, off)
        if not hdr:
            continue
        end = off + hdr['file_size']
        ok = end <= len(data)
        cls = hdr['class_defs_size']
        valid.append((off, hdr, end, ok, cls))
        print(f'    off=0x{off:x} ver={hdr["version"]} file_size={hdr["file_size"]} '
              f'end=0x{end:x} in_bounds={ok} classes={cls} methods={hdr["method_ids_size"]}')
    print(f'[+] valid-looking DEX = {len(valid)}')

    # Also scan "cdex" (compact dex, Android 10+) and "\x03\x35" any-position
    for tag in (b'cdex', b'dex\x0a035', b'dex\x0a037', b'dex\x0a038', b'dex\x0a039'):
        c = data.count(tag)
        if c:
            print(f'[+] "{tag!r}" count = {c}')

    # First 64 bytes hexdump
    print('[+] first 64 bytes:')
    for i in range(0, 64, 16):
        print('    ' + ' '.join(f'{b:02x}' for b in data[i:i + 16]))


if __name__ == '__main__':
    main()

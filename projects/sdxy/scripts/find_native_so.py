#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描 APK 内所有 arm64 SO，定位包含 K.b2s / DataComponent native 实现的 SO。"""
import zipfile
import re

APK = r"D:\reserve_agent\android\projects\sdxy\apk\sdxy.apk"
PATTERNS = [
    b'com/huachenjie/c/K',      # JNI 类名（用 / 分隔）
    b'com.huachenjie.c.K',      # 类名（用 . 分隔）
    b'b2s',
    b'DataComponent',
    b'huachenjie/running/service',
    b'huachenjie/running',
    b'RegisterNatives',
    b'Java_com_huachenjie',
]


def extract_strings(data, minlen=5):
    cur = bytearray()
    for b in data:
        if 32 <= b < 127:
            cur.append(b)
        else:
            if len(cur) >= minlen:
                yield bytes(cur)
            cur = bytearray()
    if len(cur) >= minlen:
        yield bytes(cur)


def main():
    z = zipfile.ZipFile(APK)
    so_entries = [e for e in z.infolist()
                  if e.filename.startswith('lib/arm64-v8a/') and e.filename.endswith('.so')]
    print(f'total arm64 so: {len(so_entries)}')
    for e in so_entries:
        data = z.read(e)
        hits = {}
        for pat in PATTERNS:
            if pat in data:
                hits[pat.decode('latin1')] = data.count(pat)
        if hits:
            name = e.filename.split('/')[-1]
            print(f'[+] {name} ({len(data)} bytes): {hits}')


if __name__ == '__main__':
    main()

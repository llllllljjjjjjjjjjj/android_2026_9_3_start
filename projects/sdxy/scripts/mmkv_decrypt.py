#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解密 UserConfigStorage（MMKV），提取 token。

加密链：wp.encrypt = aq.c(str, b23.a()) = Base64(AES-256-CBC(str, key=b23.a, IV=01234ABCDEF56789))
存储：d15 = MMKV.mmkvWithID（明文 MMKV），key/value 为加密后的 base64 字符串。

尝试候选密钥解密所有 base64 片段，找含 token/satoken 的明文。
"""
import base64
import re
import sys

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

IV = b'01234ABCDEF56789'
FILE = r'projects\sdxy\artifacts\UserConfigStorage'

# 候选密钥
CANDIDATES = [
    "F44B0282BEA83557",
    "4275dfd848e2eba4",   # android_id
    "huachenjie",
    "01234ABCDEF56789",
    "5f84366480455950e4a80d9a",  # r01.j (umeng appkey)
    "1320560779",
    "1111310146",
    "26082615",
    "8.6.8",
]


def pad32(key: str) -> bytes:
    b = key.encode('utf-8')
    return b[:32].ljust(32, b'\x00')


def aq_decrypt(b64: str, key: str):
    try:
        raw = base64.b64decode(b64)
    except Exception:
        return None
    if len(raw) == 0 or len(raw) % 16 != 0:
        return None
    try:
        cipher = AES.new(pad32(key), AES.MODE_CBC, IV)
        pt = unpad(cipher.decrypt(raw), AES.block_size)
        return pt.decode('utf-8', errors='replace')
    except Exception:
        return None


def main():
    data = open(FILE, 'rb').read()
    print(f'[+] file size = {len(data)}')

    # 提取所有可能的 base64 字符串（长度 >= 24，即加密后 >= 16 字节）
    b64s = set(re.findall(rb'[A-Za-z0-9+/=]{24,}', data))
    print(f'[+] base64 candidates = {len(b64s)}')

    for key in CANDIDATES:
        hits = []
        for b in b64s:
            s = b.decode('latin1')
            pt = aq_decrypt(s, key)
            if pt and ('token' in pt.lower() or 'satoken' in pt.lower() or
                       'userId' in pt or 'school' in pt.lower() or
                       '{' in pt or 'user' in pt.lower()):
                hits.append((s, pt))
        if hits:
            print(f'\n[!!!] key={key!r} 命中 {len(hits)} 个明文:')
            for b64, pt in hits:
                print(f'  密文: {b64[:50]}...')
                print(f'  明文: {pt[:500]}')
            return
        else:
            print(f'[-] key={key!r} 无命中')

    # 打印所有 base64（便于人工判断）
    print('\n[+] 所有 base64 片段:')
    for b in sorted(b64s, key=len, reverse=True)[:30]:
        print(f'  {b.decode("latin1")[:120]}')


if __name__ == '__main__':
    main()

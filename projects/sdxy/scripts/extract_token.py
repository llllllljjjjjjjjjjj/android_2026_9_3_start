#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从已登录真机一键提取登录态（token/satoken/学校信息）。

原理：UserConfigStorage(MMKV) 用 AES-256-CBC(key="F44B0282BEA83557", IV=01234ABCDEF56789) 加密，
      存 keyCommonUserInfo -> CommonUserInfo JSON（含 token/satoken/schoolCode）。

用法：python extract_token.py
"""
import base64
import json
import re
import subprocess
import sys

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

IV = b'01234ABCDEF56789'
KEY = 'F44B0282BEA83557'
ADB = r'android_mcp\toolchain\bin\windows\platform-tools\adb.exe'
REMOTE = '/data/data/com.huachenjie.shandong_school/files/mmkv/UserConfigStorage'
LOCAL = r'projects\sdxy\artifacts\UserConfigStorage'


def decrypt_file(path):
    k = KEY.encode()[:32].ljust(32, b'\x00')
    data = open(path, 'rb').read()
    b64s = set(re.findall(rb'[A-Za-z0-9+/=]{24,}', data))
    for b in b64s:
        try:
            raw = base64.b64decode(b)
            pt = unpad(AES.new(k, AES.MODE_CBC, IV).decrypt(raw), 16).decode('utf-8')
        except Exception:
            continue
        if 'satoken' in pt and 'token' in pt:
            outer = json.loads(pt)
            inner = json.loads(outer['value'])
            return inner
    return None


def main():
    print('[1/3] 拉取设备 MMKV...')
    subprocess.run([ADB, 'shell', 'su', '-c',
                    f'cp {REMOTE} /data/local/tmp/ucs; chmod 644 /data/local/tmp/ucs'],
                   check=False, capture_output=True)
    subprocess.run([ADB, 'pull', '/data/local/tmp/ucs', LOCAL],
                   check=False, capture_output=True)

    print('[2/3] 解密...')
    info = decrypt_file(LOCAL)
    if not info:
        print('[!] 解密失败，设备可能未登录或 App 未运行')
        sys.exit(1)

    print('[3/3] 提取成功:\n')
    for f in ['userId', 'token', 'satoken', 'schoolCode', 'schoolName',
              'studentNumber', 'userName', 'phone', 'userType']:
        print(f'  {f} = {info.get(f)}')

    # 保存到 json 供 dorm_run 使用
    out = r'projects\sdxy\artifacts\session.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    print(f'\n[+] 已保存到 {out}')


if __name__ == '__main__':
    main()

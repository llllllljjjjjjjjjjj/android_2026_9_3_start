#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 encKey 解密响应字段 + 测试阳光跑摘要接口。"""
import base64
import json
import os
import sys

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from simulate_sunshine_run import SdxyClient

IV = b'01234ABCDEF56789'
KEY = 'F44B0282BEA83557'
SESSION = os.path.join(os.path.dirname(__file__), '..', 'artifacts', 'session.json')


def aes_decrypt(b64):
    k = KEY.encode()[:32].ljust(32, b'\x00')
    raw = base64.b64decode(b64)
    pt = unpad(AES.new(k, AES.MODE_CBC, IV).decrypt(raw), 16)
    return pt.decode('utf-8', errors='replace')


def main():
    session = json.load(open(SESSION, encoding='utf-8'))
    c = SdxyClient(
        base_url="https://api.huachenjie.com/",
        token=session.get('token'), satoken=session.get('satoken'),
        sign_key=KEY,
    )

    # 1. 用户信息 + 解密字段验证 encKey
    print("===== 用户信息 + encKey 解密验证 =====")
    r = c.query_common_user_info()
    data = r.json().get('data', {})
    for f in ['phone', 'schoolName', 'nickName']:
        v = data.get(f)
        if v and f in ('phone', 'schoolName'):
            print(f"  {f} 密文={v} -> 明文={aes_decrypt(v)}")
        else:
            print(f"  {f} = {v}")

    # 2. 阳光跑摘要（只读查询，验证未认证账号能否进入）
    print("\n===== querySunRunAbstractInfoV2（阳光跑摘要）=====")
    r = c.query_sun_run_abstract("13", "", 1)
    print(f"HTTP {r.status_code}")
    print(r.text[:700])


if __name__ == '__main__':
    main()

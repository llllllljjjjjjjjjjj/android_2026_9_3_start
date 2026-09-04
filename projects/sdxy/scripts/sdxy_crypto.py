#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sdxy（闪动校园）请求加密与签名算法还原实现。

对应反编译源码：
- com.zj.widget.cq    : AES-256-CBC + Base64
- com.zj.widget.cl0   : Base64 编解码
- com.zj.widget.h58   : SHA256 + 字符串旋转
- com.zj.widget.c23   : 密钥/敏感字段配置
- huachenjie.sdk.http.security.core.EncryptInterceptor : 字段加解密
- huachenjie.sdk.http.interceptor.ParamsInterceptor    : sign 生成

依赖: pycryptodome  (pip install pycryptodome)
"""
import base64
import hashlib
import json

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# 固定 IV（com.zj.widget.cq.f11138a）
IV = "01234ABCDEF56789"

# 敏感字段列表（com.zj.widget.k14.d 中硬编码）
SENSITIVE_FIELDS = ["phone", "password", "userName", "schoolName", "studentNumber"]

# 字段加密密钥 key_a（com.zj.widget.r01.e，环境 9=Pro / 11=Sd 时）
# 环境 Dev/Test/Pre/Custom 时为 "huachenjie"（r01.f）
FIELD_KEY = "F44B0282BEA83557"

# sign 密钥（key_b）。
# k14.c(ctx, pwdResId) 用 BitmapFactory.decodeResource 解码 bg_contact_list，
# 但该资源是 XML shape（res/drawable/bg_contact_list.xml，非位图），
# decodeResource 对 XML 返回 null -> 走 fallback 返回 r01.e。
# 因此 sign key == 字段 key == r01.e。
SIGN_KEY = "F44B0282BEA83557"


def _pad32(key: str) -> bytes:
    """com.zj.widget.cq.f(str): UTF-8 字节，截断/右补零到 32 字节（AES-256）。"""
    b = key.encode("utf-8")
    if len(b) == 32:
        return b
    out = bytearray(32)
    n = min(len(b), 32)
    out[:n] = b[:n]
    return bytes(out)


def encrypt_field(plain: str, key: str) -> str:
    """com.zj.widget.cq.c(str, str): AES-256-CBC 加密 + Base64。"""
    cipher = AES.new(_pad32(key), AES.MODE_CBC, IV.encode("utf-8"))
    ct = cipher.encrypt(pad(plain.encode("utf-8"), AES.block_size))
    return base64.b64encode(ct).decode("utf-8")


def decrypt_field(ciphertext: str, key: str) -> str:
    """com.zj.widget.cq.a(str, str): Base64 解码 + AES-256-CBC 解密。"""
    raw = base64.b64decode(ciphertext)
    cipher = AES.new(_pad32(key), AES.MODE_CBC, IV.encode("utf-8"))
    return unpad(cipher.decrypt(raw), AES.block_size).decode("utf-8")


def sha256_rotate(s: str) -> str:
    """com.zj.widget.h58.c(str) = a(str, SHA256): SHA256 hex 后字符串旋转。

    hex -> 末8位 + 中间(len-16) + 前8位
    """
    h = hashlib.sha256(s.encode("utf-8")).hexdigest()
    if len(h) < 16:
        return h
    return h[-8:] + h[8:-8] + h[:8]


def make_sign(params: dict, sign_key: str) -> str:
    """com.zj.widget.ParamsInterceptor.getSign:
    sign = AES-256-CBC(SHA256_rotate(JSON(params)), sign_key) -> Base64
    """
    json_str = json.dumps(params, ensure_ascii=False, separators=(",", ":"))
    rotated = sha256_rotate(json_str)
    return encrypt_field(rotated, sign_key)


def encrypt_form_body(params: dict, field_key: str) -> dict:
    """EncryptInterceptor.d(): 对敏感字段值做 AES 加密，其余原样。"""
    out = {}
    for k, v in params.items():
        if k in SENSITIVE_FIELDS and isinstance(v, str):
            out[k] = encrypt_field(v, field_key)
        else:
            out[k] = v
    return out


def build_headers(api_path: str, extra: dict = None) -> dict:
    """EncryptInterceptor.l(): 从 URL path 前三段生成 app/api/v，附加公共头。

    URL 形如 https://host/run-front/xxx/yyy
      pathSegments[0]=app, [1]=api, [2]=v
    """
    segs = [s for s in api_path.split("/") if s]
    headers = {
        "app": segs[0] if len(segs) > 0 else "",
        "api": segs[1] if len(segs) > 1 else "",
        "v": segs[2] if len(segs) > 2 else "",
        "pv": "2",
        "e": "0",
        "User-Agent": "okhttp/3.12.1",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    if extra:
        headers.update(extra)
    return headers


if __name__ == "__main__":
    # 自检：算法一致性
    k = FIELD_KEY
    pt = "13800138000"
    ct = encrypt_field(pt, k)
    assert decrypt_field(ct, k) == pt, "roundtrip failed"
    print(f"roundtrip ok: {pt} -> {ct[:24]}...")
    s = make_sign({"phone": "13800138000", "password": "abc123"}, k)
    print(f"sign sample: {s}")
    print("sha256_rotate('test') =", sha256_rotate("test"))

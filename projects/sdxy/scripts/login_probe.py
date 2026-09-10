#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""登录接口在线实证（LOGIN_API.md §6 待实证项闭合）。

流程：loginCheck 预检（真实 App 形状：e:1 + sign）→ loginPassword（字段加密 + e:1，
先按模拟器原状不带 sign；若失败再带 sign 对照），观察服务端是否强制校验 sign。
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from simulate_sunshine_run import SdxyClient, COMMON_PARAMS

PHONE = "13407006275"
PWD = "060916Ljj"
BASE = "https://api.huachenjie.com/"


def show(tag, resp, body_ok=True):
    print(f"\n===== {tag} =====")
    print(f"HTTP {resp.status_code}")
    ct = resp.headers.get("Content-Type", "")
    print(f"Content-Type: {ct}")
    txt = resp.text
    print(txt[:1200])
    return txt


def main():
    c = SdxyClient(base_url=BASE, sign_key="F44B0282BEA83557")

    # 1) loginCheck 预检（e:1 + 公共参数 + sign，贴近真实 App 形状）
    r1 = c.post_form("run-front/auth/loginCheck", {"loginName": PHONE},
                     with_sign=True, extra={"e": "1"})
    show("loginCheck(with sign)", r1)

    time.sleep(3)

    # 2) loginPassword —— 模拟器原状：不带 sign（验证服务端是否强制）
    r2 = c.login_password(PHONE, PWD)
    t2 = show("loginPassword(no sign)", r2)
    return t2


if __name__ == "__main__":
    main()

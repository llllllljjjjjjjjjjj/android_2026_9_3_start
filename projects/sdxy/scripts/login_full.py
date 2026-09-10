#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""1600 滑块验证码全自动 solver + 登录（密码/发码）。

已标定映射（真机成功样本测得）：
  pointJson = AES-128-ECB(JSON({x, y:15}), key=Ukp3hmSe7BmMcgbE)
  x = 模板匹配中心(C) - 13.5   # C 为 matchTemplate 最佳匹配中心 x（310 设计体系）
流程：getCaptcha -> 下载原图/拼块 -> 定位 C -> 算 x -> check -> captchaPoint
      -> loginPassword(带 captchaPoint) / getAuthCode(带 captchaPoint) 完成登录/发码
"""
import os
import sys
import json
import cv2
import numpy as np
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sdxy_crypto import make_sign, build_headers, encrypt_field
from captcha_solver import get_captcha, check, aes_ecb_enc, STATIC_KEY

BASE = "https://api.huachenjie.com/"


def _download(url):
    s = requests.Session(); s.trust_env = False
    return s.get(url, timeout=20).content


def locate_cx(orig, pz):
    bg = cv2.imdecode(np.frombuffer(orig, np.uint8), cv2.IMREAD_COLOR)
    pj = cv2.imdecode(np.frombuffer(pz, np.uint8), cv2.IMREAD_UNCHANGED)
    gz = cv2.cvtColor(bg, cv2.COLOR_BGR2GRAY)
    if pj.shape[2] == 4:
        res = cv2.matchTemplate(gz, cv2.cvtColor(pj[:, :, :3], cv2.COLOR_BGR2GRAY),
                                cv2.TM_CCOEFF_NORMED, mask=pj[:, :, 3])
    else:
        res = cv2.matchTemplate(gz, cv2.cvtColor(pj, cv2.COLOR_BGR2GRAY), cv2.TM_CCOEFF_NORMED)
    _, _, _, ml = cv2.minMaxLoc(res)
    return ml[0] + pj.shape[1] / 2.0, float(cv2.minMaxLoc(res)[1])


def solve_captcha_point(client):
    """跑完整滑块，成功返回 captchaPoint；失败返回 (None, 状态)。"""
    d = get_captcha(client)
    token = d["token"]
    orig = _download(d["originalImageUrl"])
    pz = _download(d["jigsawImageUrl"])
    C, score = locate_cx(orig, pz)
    x = round(C - 13.5, 1)
    cc = {"x": x, "y": 15}
    point_json = aes_ecb_enc(json.dumps(cc, separators=(",", ":")), STATIC_KEY)
    r = check(client, token, point_json)
    try:
        ok = r.json().get("data", {}).get("result") is True
    except Exception:
        ok = False
    return (point_json if ok else None), {"token": token, "C": C, "score": score,
                                          "x": x, "ok": ok}


def main():
    from simulate_sunshine_run import SdxyClient
    c = SdxyClient(base_url=BASE, sign_key="F44B0282BEA83557")
    c.session.trust_env = False
    phone = "13407006275"

    print("== 跑滑块验证码 ==", flush=True)
    cp, info = solve_captcha_point(c)
    print("slider:", info, flush=True)
    if not cp:
        print("!!! 滑块未过", flush=True); return
    print("captchaPoint:", cp[:40] + "...", flush=True)

    print("== 密码登录 ==", flush=True)
    r = c.post_form("run-front/auth/loginPassword",
                    {"loginName": phone, "password": "060916Ljj", "captchaPoint": cp},
                    with_sign=False, encrypt=True, extra={"e": "1"})
    j = r.json()
    print("code:", j.get("code"), "msg:", (j.get("message") or "")[:60], flush=True)
    data = j.get("data") or {}
    if j.get("code") == 0 and data.get("token"):
        print("=== 登录成功 ===", flush=True)
        print("userId:", data.get("userId"))
        print("token:", (data.get("token") or "")[:60], "...")
        print("satoken:", data.get("satoken"))
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "..", "artifacts", "session.json"), "w", encoding="utf-8") as f:
            json.dump({"userId": data.get("userId"), "token": data.get("token"),
                       "satoken": data.get("satoken")}, f, ensure_ascii=False, indent=2)
        print("已写入 artifacts/session.json")
    else:
        print("登录结果:", j)


if __name__ == "__main__":
    main()

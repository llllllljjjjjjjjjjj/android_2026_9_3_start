#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""1600 图形滑块验证码 solver（blockPuzzle，自研 H5）。
流程复刻:
 1) POST /run-front/captcha/get  {captchaType:"blockPuzzle"} -> {originalImageUrl, jigsawImageUrl, token}
 2) 图像定位缺口 x（310 设计体系）
 3) pointJson = AES-128-ECB(JSON({x, y:15}), static_secretKey)  # Ukp3hmSe7BmMcgbE
 4) POST /run-front/captcha/check {captchaType, pointJson, token}
 5) 成功 => data 内含 captchaPoint(=pointJson)，供 loginPassword/getAuthCode 提交
"""
import io
import sys
import os
import json
import numpy as np
import cv2
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sdxy_crypto import make_sign, build_headers

STATIC_KEY = "Ukp3hmSe7BmMcgbE"   # App JavascriptApi.getSecretKey（16B AES-128-ECB）
BASE = "https://api.huachenjie.com/"


def _pad(s):
    return s + chr(16 - len(s) % 16) * (16 - len(s) % 16)


def aes_ecb_enc(plain: str, key: str) -> str:
    """CryptoJS AES-ECB Pkcs7 -> toString() 为 Base64 密文（CipherParams）。"""
    import base64
    from Crypto.Cipher import AES
    k = key.encode("utf-8")
    c = AES.new(k, AES.MODE_ECB)
    return base64.b64encode(c.encrypt(_pad(plain).encode("utf-8"))).decode()


def locate_gap(orig_bytes: bytes, pz_bytes: bytes):
    """返回候选 x（310 体系 px）列表：模板匹配 + 边缘对。"""
    import cv2 as _cv
    import numpy as np
    bg = _cv.imdecode(np.frombuffer(orig_bytes, np.uint8), _cv.IMREAD_COLOR)
    pz = _cv.imdecode(np.frombuffer(pz_bytes, np.uint8), _cv.IMREAD_UNCHANGED)
    W, H = bg.shape[1], bg.shape[0]
    can = []
    # 模板匹配（RGB，忽略 alpha）取 top3
    g = _cv.cvtColor(bg, _cv.COLOR_BGR2GRAY)
    if pz.shape[2] == 4:
        mask = pz[:, :, 3]
        pzrgb = pz[:, :, :3]
        t = _cv.cvtColor(pzrgb, _cv.COLOR_BGR2GRAY)
        res = _cv.matchTemplate(g, t, _cv.TM_CCOEFF_NORMED, mask=mask)
    else:
        t = _cv.cvtColor(pz, _cv.COLOR_BGR2GRAY)
        res = _cv.matchTemplate(g, t, _cv.TM_CCOEFF_NORMED)
    fl = res.flatten()
    idx = np.argsort(fl)[::-1][:3]
    hh, ww = t.shape
    for ind in idx:
        x0, y0 = divmod(int(ind), res.shape[1])
        can.append((x0 + ww / 2, float(fl[ind])))
    # 边缘对 (y 55..115)
    gx = _cv.Sobel(g, _cv.CV_64F, 1, 0, ksize=3)
    mag = np.hypot(gx, _cv.Sobel(g, _cv.CV_64F, 0, 1, ksize=3))
    band = mag[55:116, :].mean(axis=0)
    thr = band.mean() + 1.5 * band.std()
    peaks = [int(i) for i in np.where(band > thr)[0]]
    cls = []
    if peaks:
        cur = [peaks[0]]
        for v in peaks[1:]:
            if v - cur[-1] <= 3:
                cur.append(v)
            else:
                cls.append(int(np.mean(cur))); cur = [v]
        cls.append(int(np.mean(cur)))
    for i in range(len(cls)):
        for j in range(i + 1, len(cls)):
            d = cls[j] - cls[i]
            if 40 <= d <= 56:
                can.append(((cls[i] + cls[j]) / 2, 0.0))
    return W, can


def get_captcha(client):
    r = client.post_form("run-front/captcha/get", {"captchaType": "blockPuzzle"},
                         with_sign=True, encrypt=False)
    d = r.json().get("data", {})
    return d


def check(client, token, point_json):
    r = client.post_form("run-front/captcha/check",
                         {"captchaType": "blockPuzzle", "pointJson": point_json, "token": token},
                         with_sign=True, encrypt=False)
    return r


def solve_easy(client, token=None, orig_url=None, pz_url=None, debug=False):
    """一次 get + 定位 + 候选 x 提交 check，成功返回 pointJson 与 data。"""
    d = get_captcha(client)
    token = token or d.get("token")
    ou = orig_url or d.get("originalImageUrl")
    pu = pz_url or d.get("jigsawImageUrl")
    ob = requests.get(ou, timeout=20).content
    pb = requests.get(pu, timeout=20).content
    W, can = locate_gap(ob, pb)
    best = None
    for x, score in can:
        x = max(0.0, min(float(W), x))
        for dx in (0, -3, 3, -6, 6, -10, 10, -14, 14):
            xx = round(x + dx, 1)
            if xx < 0 or xx > W:
                continue
            pt = json.dumps({"x": xx, "y": 15}, separators=(",", ":"))
            pj = aes_ecb_enc(pt, STATIC_KEY)
            r = check(client, token, pj)
            try:
                j = r.json()
            except Exception:
                j = {"raw": r.text[:200]}
            res = j.get("data", {})
            if debug:
                print(f"  try x={xx} code={j.get('code')} data={j.get('data')}", flush=True)
            if j.get("code") == 0 and res.get("result") is True:
                best = pj
                break
        if best:
            break
    return best, d


if __name__ == "__main__":
    from simulate_sunshine_run import SdxyClient
    c = SdxyClient(base_url=BASE, sign_key="F44B0282BEA83557")
    pj, d = solve_easy(c, debug=True)
    print("\nRESULT pointJson:", pj)
    print("captcha data:", d.get("token"))
    if pj:
        print("\n===== 尝试用 captchaPoint 密码登录 =====")
        r = c.post_form("run-front/auth/loginPassword",
                        {"loginName": "13407006275", "password": "060916Ljj",
                         "captchaPoint": pj},
                        with_sign=False, encrypt=True, extra={"e": "1"})
        print(r.content.decode("utf-8", "replace")[:800])

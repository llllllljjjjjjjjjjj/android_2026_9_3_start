#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sdxy（闪动校园）首页 -> 运动 -> 阳光跑 接口模拟客户端。

基于反编译还原的算法（见 sdxy_crypto.py）与接口（ISunshineApi/IRunApi）。

使用前提：
  1. 已有登录 token（Authorization）与 satoken；
  2. 确认 sign 密钥（SIGN_KEY）。字段密钥 FIELD_KEY 已静态确定。
     动态获取方式见 projects/sdxy/hooks/（设备联网后运行）：
       .venv-frida-16.5.7/Scripts/python.exe projects/sdxy/scripts/frida_read_keys.py <pid>
  3. 确认环境 BaseUrl：
       env 9  (Pro)  -> https://api.huachenjie.com/
       env 11 (Sd)   -> https://sd-api.huachenjie.com/
"""
import json
import time

import requests
import urllib3

# 环境时间超前导致证书"过期"，模拟场景禁用 SSL 校验
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from sdxy_crypto import (
    FIELD_KEY,
    SIGN_KEY,
    build_headers,
    encrypt_field,
    make_sign,
    SENSITIVE_FIELDS,
)

# 公共请求参数（e58.decorateParams 装饰，对应 mo1 字段）
# 来源：d11 常量 + 设备信息（真机 Pixel 4）
COMMON_PARAMS = {
    "appVersion": "8.6.8",
    "buildVersion": "26082615",
    "appCode": "SD001",
    "deviceId": "4275dfd848e2eba4",   # android_id
    "platform": "2",                  # 设备类型（Android）
    "modelName": "Google|Pixel 4",
    "systemVersion": "10",
    "channel": "other",
}


class SdxyClient:
    def __init__(self, base_url="https://sd-api.huachenjie.com/",
                 token=None, satoken=None, sign_key=SIGN_KEY):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.satoken = satoken
        self.user_id = None
        self.sign_key = sign_key or FIELD_KEY  # sign key == 字段 key（XML shape 导致 fallback）
        self.session = requests.Session()
        self.session.verify = False

    def _headers(self, api_path, with_sign=True, sign_map=None, extra=None):
        h = build_headers(api_path)
        if self.token:
            h["Authorization"] = self.token
        if self.satoken:
            h["satoken"] = self.satoken
        if with_sign and sign_map is not None:
            h["sign"] = make_sign(sign_map, self.sign_key)
        if extra:
            h.update(extra)
        return h

    def post_form(self, api_path, params, with_sign=True, encrypt=True, extra=None):
        """表单请求 -> 转 JSON -> 敏感字段加密 -> 加公共参数 -> 计算 sign -> application/json 发送。"""
        url = f"{self.base_url}/{api_path.lstrip('/')}"
        # 1. 敏感字段加密
        body = {k: (encrypt_field(str(v), FIELD_KEY) if k in SENSITIVE_FIELDS else v)
                for k, v in params.items()}
        # 2. 加公共参数（e58.decorateParams）
        body.update(COMMON_PARAMS)
        body["timestamp"] = str(int(time.time() * 1000))
        # 3. sign 基于装饰后的参数（字符串化）
        sign_map = {k: str(v) for k, v in body.items()}
        headers = self._headers(api_path, with_sign, sign_map, extra=extra)
        headers["Content-Type"] = "application/json"
        data = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
        resp = self.session.post(url, headers=headers, data=data, timeout=15)
        return resp

    def _add_common(self, body):
        out = dict(body)
        out.update(COMMON_PARAMS)
        out.setdefault("timestamp", str(int(time.time() * 1000)))
        return out

    def post_json(self, api_path, body_dict, with_sign=False):
        """JSON body 请求（finishSunRun_v2 等），自动加公共参数。"""
        url = f"{self.base_url}/{api_path.lstrip('/')}"
        body = self._add_common(body_dict)
        headers = self._headers(api_path, with_sign=False)
        headers["Content-Type"] = "application/json"
        if with_sign:
            headers["sign"] = make_sign({k: str(v) for k, v in body.items()}, self.sign_key)
        data = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
        resp = self.session.post(url, headers=headers, data=data, timeout=15)
        return resp

    # ---- 登录与基础信息 ----

    def login_password(self, login_name, password, captcha_point=None):
        """密码登录（loginPassword）。password 走 AES 加密，header 带 e:1。"""
        params = {"loginName": login_name, "password": password}
        if captcha_point:
            params["captchaPoint"] = captcha_point
        return self.post_form("run-front/auth/loginPassword", params,
                              with_sign=False, extra={"e": "1"})

    def login_apply_token(self, login_name, password, captcha_point=None):
        """登录并自动提取 token/satoken/userId。"""
        resp = self.login_password(login_name, password, captcha_point)
        try:
            data = resp.json().get("data", {})
            self.token = data.get("token")
            self.satoken = data.get("satoken")
            self.user_id = data.get("userId")
        except Exception:
            pass
        return resp

    def query_common_user_info(self):
        """查询用户信息（含 schoolCode/schoolName/semesterCode）。"""
        return self.post_form("run-front/account/queryCommonUserInfo", {})

    def semester_selector(self):
        """学期选择列表。"""
        return self.post_form("run-front/attend/semesterSelector", {})

    def query_school_fences(self, school_code):
        """查学校围栏（fenceCode + 围栏中心 + 打卡点规则）。"""
        return self.post_form("run-front/school/querySchoolFences",
                              {"schoolCode": school_code})

    # ---- 阳光跑接口 ----

    def query_sun_run_abstract(self, semester_code, run_plan_code, sport_type):
        """进入阳光跑页：查询摘要。"""
        return self.post_form(
            "run-front/run/querySunRunAbstractInfoV2",
            {"semesterCode": semester_code, "runPlanCode": run_plan_code,
             "sportType": sport_type},
        )

    def check_sun_run_config(self, school_code, sub_school_code, target_distance,
                             activity_code, run_plan_code, fence_code, sport_type):
        """开始跑步前：检查配置。"""
        return self.post_form(
            "run-front/run/checkSunRunConfig",
            {"schoolCode": school_code, "subSchoolCode": sub_school_code,
             "targetDistance": target_distance, "activityCode": activity_code,
             "runPlanCode": run_plan_code, "fenceCode": fence_code,
             "sportType": sport_type},
        )

    def start_sun_run(self, school_code, fence_code, activity_code, lat, lng,
                      target_distance, use_credit_sword, run_plan_code, sport_type):
        """开始阳光跑。"""
        return self.post_form(
            "run-front/run/startSunRun_v2",
            {"schoolCode": school_code, "fenceCode": fence_code,
             "activityCode": activity_code, "lat": lat, "lng": lng,
             "targetDistance": target_distance,
             "useCreditSword": "true" if use_credit_sword else "false",
             "runPlanCode": run_plan_code, "sportType": sport_type},
        )

    def upload_run_record(self, record_body: dict):
        """上传跑步记录（IRunApi.h 带 sign header，body 为 JSON）。"""
        api_path = "run-front/run/uploadRunRecord"
        sign = make_sign(record_body, self.sign_key)
        return self.post_json_with_sign(api_path, record_body, sign)

    def post_json_with_sign(self, api_path, body_dict, sign=None):
        url = f"{self.base_url}/{api_path.lstrip('/')}"
        body = self._add_common(body_dict)
        headers = self._headers(api_path, with_sign=False)
        headers["Content-Type"] = "application/json"
        if sign is None:
            sign = make_sign({k: str(v) for k, v in body.items()}, self.sign_key)
        headers["sign"] = sign
        data = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
        return self.session.post(url, headers=headers, data=data, timeout=15)

    def finish_sun_run(self, finish_body: dict):
        """结束阳光跑（finishSunRun_v2，JSON body）。"""
        return self.post_json("run-front/run/finishSunRun_v2", finish_body)

    def page_sun_run_record(self, page_size, page_num, semester_code, run_plan_code):
        """阳光跑记录列表。"""
        return self.post_form(
            "run-front/run/pageSunRunRecord",
            {"pageSize": page_size, "pageNum": page_num,
             "semesterCode": semester_code, "runPlanCode": run_plan_code},
        )

    def query_unfinish_run(self, sport_type=1):
        """查询未完成跑步（断点续跑）。"""
        return self.post_form(
            "run-front/run/queryUnFinishRun",
            {"sportType": sport_type},
        )


def demo_flow():
    """首页 -> 运动 -> 阳光跑 完整调用链示例（需要真实 token 与网络）。"""
    c = SdxyClient(
        base_url="https://sd-api.huachenjie.com/",
        token="<Authorization token>",
        satoken="<satoken>",
        sign_key=None,  # 填真实 sign key，或设备联网后动态获取
    )
    print("[1] 进入阳光跑页，查询摘要")
    r1 = c.query_sun_run_abstract(semester_code="<sem>", run_plan_code="<plan>", sport_type=1)
    print("   ", r1.status_code, r1.text[:200])

    print("[2] 检查跑步配置")
    r2 = c.check_sun_run_config("<school>", "<sub>", 2000, "<act>", "<plan>", "<fence>", 1)
    print("   ", r2.status_code, r2.text[:200])

    print("[3] 开始阳光跑")
    r3 = c.start_sun_run("<school>", "<fence>", "<act>", 36.0, 117.0, 2000, False, "<plan>", 1)
    print("   ", r3.status_code, r3.text[:200])

    print("[4] 结束阳光跑（示例 body，字段按业务补全）")
    r4 = c.finish_sun_run({"runRecordCode": "<code>", "distance": 2000, "duration": 600})
    print("   ", r4.status_code, r4.text[:200])


if __name__ == "__main__":
    demo_flow()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用当前登录 token 测试只读接口（非作弊），验证签名算法 + 观察未认证账号响应。"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from simulate_sunshine_run import SdxyClient

SESSION = os.path.join(os.path.dirname(__file__), '..', 'artifacts', 'session.json')


def main():
    session = json.load(open(SESSION, encoding='utf-8'))
    token = session.get('token')
    satoken = session.get('satoken')
    school_code = session.get('schoolCode')
    print(f"账号: userId={session.get('userId')} phone={session.get('phone')} "
          f"studentNumber='{session.get('studentNumber')}' school={session.get('schoolName')}")

    c = SdxyClient(
        base_url="https://api.huachenjie.com/",
        token=token, satoken=satoken, sign_key="F44B0282BEA83557",
    )

    tests = [
        ("queryCommonUserInfo（用户信息）", lambda: c.query_common_user_info()),
        ("semesterSelector（学期列表）", lambda: c.semester_selector()),
        ("querySchoolFences（学校围栏）", lambda: c.query_school_fences(school_code)),
        ("queryUnFinishRun（未完成跑步）", lambda: c.query_unfinish_run(1)),
    ]

    for name, fn in tests:
        print(f"\n===== {name} =====")
        try:
            r = fn()
            print(f"HTTP {r.status_code}")
            print(r.text[:600])
        except Exception as e:
            print(f"ERR: {e}")


if __name__ == '__main__':
    main()

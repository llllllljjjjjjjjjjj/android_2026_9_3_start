#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宿舍打卡跑步（阳光跑）一键模拟。

完整流程：
  登录 -> 查用户信息(schoolCode) -> 查学期(semesterCode) -> 查围栏(fenceCode+坐标)
  -> 检查配置(配速规则+人脸开关) -> 开始跑(runRecordCode+打卡点)
  -> 伪造轨迹(绕打卡点) -> 上传轨迹/步数/步幅 -> 结束跑

用法：
  python dorm_run.py <学号/账号> <密码>
"""
import json
import os
import sys

from simulate_sunshine_run import SdxyClient
from sdxy_run_simulator import RunDataSimulator, extract_path_from_start

SESSION_FILE = os.path.join(os.path.dirname(__file__), '..', 'artifacts', 'session.json')


def load_session():
    """从 session.json 读取已提取的登录态。"""
    p = os.path.normpath(SESSION_FILE)
    if os.path.exists(p):
        with open(p, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def get_data(resp, label):
    """从响应提取 data，失败打印并退出。"""
    try:
        j = resp.json()
    except Exception:
        print(f'[!] {label} 响应非 JSON: {resp.text[:300]}')
        return None
    if j.get('code') not in (0, 200) and j.get('code') != 200:
        print(f'[!] {label} 业务失败 code={j.get("code")} msg={j.get("message")}')
        print(f'    原始: {resp.text[:400]}')
        return None
    return j.get('data')


def main(login_name=None, password=None, base_url="https://api.huachenjie.com/"):
    # 优先从 session.json 读已提取的登录态
    sess = load_session()
    if sess and sess.get('token'):
        c = SdxyClient(base_url=base_url, token=sess['token'], satoken=sess.get('satoken'))
        c.user_id = sess.get('userId')
        school_code = sess.get('schoolCode', '')
        school_name = sess.get('schoolName', '')
        print(f'[1/8] 使用已提取登录态：{school_name} 学号 {sess.get("studentNumber")}')
    elif login_name and password:
        c = SdxyClient(base_url=base_url)
        print('[1/8] 登录...')
        resp = c.login_apply_token(login_name, password)
        if not c.token:
            print(f'[!] 登录失败: {resp.text[:400]}')
            return
        print(f'     token 获取成功，userId={c.user_id}')
        data = get_data(c.query_common_user_info(), '用户信息')
        if not data:
            return
        school_code = data.get('schoolCode', '')
        school_name = data.get('schoolName', '')
        print(f'     学校: {school_name} ({school_code})')
    else:
        print('未提供登录态。用法：')
        print('  1) 真机已登录：先运行 python extract_token.py 提取，再直接运行本脚本')
        print('  2) 或 python dorm_run.py <学号> <密码> 走登录')
        return

    # 3. 查学期 -> semesterCode
    print('[3/8] 查询学期...')
    sem_data = get_data(c.semester_selector(), '学期')
    semester_code = ''
    if isinstance(sem_data, list) and sem_data:
        semester_code = sem_data[0].get('semesterCode', '')
    print(f'     semesterCode={semester_code}')

    # 4. 查围栏 -> fenceCode + 中心坐标 + 打卡点规则
    print('[4/8] 查询学校围栏...')
    fence_data = get_data(c.query_school_fences(school_code), '围栏')
    if not fence_data:
        return
    fences = fence_data if isinstance(fence_data, list) else [fence_data]
    # 选一个开放中的围栏
    fence = None
    for f in fences:
        if f.get('openStatus', True):
            fence = f
            break
    if fence is None:
        fence = fences[0]
    fence_code = fence.get('fenceCode', '')
    center_lat = fence.get('lat', 0)
    center_lng = fence.get('lng', 0)
    required_dist = fence.get('distance', 2000)
    clock_mode = fence.get('clockMode', 0)
    print(f'     围栏: {fence.get("fenceName","")} code={fence_code} '
          f'中心=({center_lat},{center_lng}) 要求距离={required_dist}m '
          f'打卡模式={clock_mode} 必需点={fence.get("requiredPointCounts",0)}')

    # 4.5 清理未完成跑步（上次失败残留）
    unf = get_data(c.query_unfinish_run(1), '未完成跑步')
    if unf and unf.get('runRecordCode'):
        old_code = unf.get('runRecordCode')
        print(f'     发现未完成跑步 {old_code}，先异常结束...')
        r = c.post_json("run-front/run/abnormalFinishSunRun",
                        {"runRecordCode": old_code, "abnormalCodes": [2072]},
                        with_sign=True)
        jr = r.json()
        print(f'     清理结果: code={jr.get("code")} msg={jr.get("message")}')

    # 5. 检查配置 -> 配速规则 + 人脸开关
    print('[5/8] 检查跑步配置...')
    cfg_data = get_data(c.check_sun_run_config(
        school_code, '', required_dist, '', '', fence_code, 1), '配置')
    if not cfg_data:
        return
    rule = {
        'minPace': cfg_data.get('minPace', 300),
        'maxPace': cfg_data.get('maxPace', 540),
        'singleMinDistance': cfg_data.get('singleMinDistance', required_dist),
        'requiredPointCounts': cfg_data.get('requiredPointCounts', 0),
        'optionalPointGoalCounts': cfg_data.get('optionalPointGoalCounts', 0),
    }
    face_auth = cfg_data.get('faceAuth', False)
    face_enabled = cfg_data.get('faceEnabled', False)
    run_scene = cfg_data.get('runScene', 0)
    print(f'     配速范围 {rule["minPace"]}~{rule["maxPace"]} s/km，'
          f'最低距离 {rule["singleMinDistance"]}m')
    print(f'     人脸: faceAuth={face_auth} faceEnabled={face_enabled} '
          f'runScene={run_scene}')
    if face_auth and face_enabled:
        print('[!] 警告：该校开启强制人脸认证，纯数据模拟无法通过，需真人脸配合')

    # 6. 开始跑 -> runRecordCode + targetPoints
    print('[6/8] 开始阳光跑...')
    start_data = get_data(c.start_sun_run(
        school_code, fence_code, '', center_lat, center_lng,
        required_dist, False, '', 1), '开始跑')
    if not start_data:
        return
    run_record_code = start_data.get('runRecordCode', '')
    target_points = start_data.get('targetPoints', [])
    cheat_level = start_data.get('cheatLevel', 0)
    print(f'     runRecordCode={run_record_code} 打卡点={len(target_points)} '
          f'cheatLevel={cheat_level}')
    for tp in target_points:
        print(f'      打卡点 code={tp.get("code")} ({tp.get("lat")},{tp.get("lng")}) '
              f'type={tp.get("type")}')

    # 7. 生成轨迹 + 上传
    print('[7/8] 生成轨迹并上传...')
    # 路径：围栏中心 -> 各打卡点(按 sort) -> 围栏中心
    path = extract_path_from_start({'targetPoints': target_points}, center_lat, center_lng)
    sim = RunDataSimulator(c, run_record_code, start_data, rule,
                           {'stepInterval': 30, 'paceInterval': 60, 'strideInterval': 60},
                           sport_type=1, run_scene=run_scene)
    sim.generate(path, distance_m=required_dist)
    sim.mark_pass_points(target_points)
    up = sim.upload_all()
    for k, v in up.items():
        ok = v.status_code == 200 and v.json().get('code') in (0, 200, None)
        print(f'     {k}: HTTP {v.status_code} {"OK" if ok else v.text[:150]}')

    # 8. 结束跑
    print('[8/8] 结束阳光跑...')
    finish_body = sim.build_finish_body()
    fin = c.finish_sun_run(finish_body)
    print(f'     HTTP {fin.status_code}')
    fd = get_data(fin, '结束')
    if fd:
        print(f'     status={fd.get("status")} '
              f'validDistance={fd.get("validDistance")} '
              f'appealFlag={fd.get("appealFlag")} '
              f'recheckStatus={fd.get("recheckStatus")}')
    else:
        print(f'     原始: {fin.text[:500]}')


if __name__ == '__main__':
    if len(sys.argv) == 1:
        # token 模式（先用 extract_token.py 提取登录态）
        main()
    elif len(sys.argv) >= 3:
        url = sys.argv[3] if len(sys.argv) > 3 else "https://api.huachenjie.com/"
        main(sys.argv[1], sys.argv[2], url)
    else:
        print('用法:')
        print('  python dorm_run.py                # 使用已提取的 token（先跑 extract_token.py）')
        print('  python dorm_run.py <学号> <密码>   # 账号密码登录')
        sys.exit(1)

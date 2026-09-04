#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sdxy（闪动校园）阳光跑完整模拟：轨迹生成 + 数据上报 + 结束跑。

依据反编译源码还原的数据结构与检测规则：
- RunLatLng      : GPS 轨迹点（uploadRunRecord）
- IntervalStep   : 步数区间（uploadStepsRecord）
- StopRunUtils.q : finishSunRun_v2 body 构造
- hp8.e          : 服务端无效原因规则（距离/配速/打卡点/步幅）
- CHEAT_DETECTION.md : 完整检测机制

用途：生成一份数据自洽、可绕过常规校验的跑步数据，并走完
startSunRun_v2 -> 上传 -> finishSunRun_v2 全链路。
"""
import json
import math
import random
import time

from sdxy_crypto import FIELD_KEY, make_sign


def extract_path_from_start(start_entity, start_lat, start_lng):
    """
    从 startSunRun_v2 响应提取打卡点坐标，构造伪造轨迹的路径点。
    start_entity: StartRunEntity dict，含 targetPoints [{lat,lng,code,type,sort,...}]
    start_lat/start_lng: 起点坐标（围栏内，可取自当前真实定位或围栏中心）
    返回: [(lat,lng)] 起点 -> 按 sort 排序的打卡点 -> 起点（闭合）
    """
    pts = [(start_lat, start_lng)]
    tps = sorted(start_entity.get("targetPoints", []), key=lambda p: p.get("sort", 0))
    for tp in tps:
        pts.append((tp.get("lat"), tp.get("lng")))
    # 闭合回到起点（围栏内绕圈），保证轨迹完整
    pts.append((start_lat, start_lng))
    return pts


def haversine(lat1, lng1, lat2, lng2):
    """两点球面距离（米）。"""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def interpolate(lat1, lng1, lat2, lng2, frac):
    return lat1 + (lat2 - lat1) * frac, lng1 + (lng2 - lng1) * frac


class RunTrajectory:
    """GPS 轨迹生成器：起点 -> 途经点 -> 终点，插值成连续轨迹。"""

    def __init__(self, points, distance_m, duration_s, min_pace_s_per_km,
                 max_pace_s_per_km, sample_interval_s=2.0, seed=None):
        """
        points: [(lat, lng)] 路径关键点（含起点、打卡点、终点，按顺序）
        distance_m: 期望总距离（米）
        duration_s: 期望总时长（秒）
        min_pace_s_per_km / max_pace_s_per_km: 配速区间（秒/公里）
        """
        self.points = points
        self.distance_m = distance_m
        self.duration_s = duration_s
        self.min_pace = min_pace_s_per_km
        self.max_pace = max_pace_s_per_km
        self.sample_interval = sample_interval_s
        self.rng = random.Random(seed)

    def _segment_lengths(self):
        return [haversine(self.points[i][0], self.points[i][1],
                          self.points[i + 1][0], self.points[i + 1][1])
                for i in range(len(self.points) - 1)]

    def generate(self, start_ts_ms, start_lat, start_lng):
        """生成轨迹点列表。返回 RunLatLng 风格的 dict 列表。"""
        segs = self._segment_lengths()
        total_path = sum(segs)
        # 每段按距离比例分配时长，速度在配速区间内微调
        n_segments = len(segs)
        seg_durations = [self.duration_s * s / total_path for s in segs] if total_path > 0 \
            else [self.duration_s / n_segments] * n_segments

        track = []
        idx = 0
        run_time = 0
        cur_ts = start_ts_ms
        base_lat, base_lng = start_lat, start_lng

        # 第 0 个点（起点）
        track.append(self._point(idx, base_lat, base_lng, 0, run_time, cur_ts, 0))
        idx += 1

        for si in range(n_segments):
            p1 = self.points[si]
            p2 = self.points[si + 1]
            seg_len = segs[si]
            seg_dur = seg_durations[si]
            n_steps = max(1, int(round(seg_dur / self.sample_interval)))
            # 每步速度在配速区间内随机微调（保持平均配速在区间中值附近）
            base_speed = (seg_len / seg_dur) if seg_dur > 0 else 3.0  # m/s
            for k in range(1, n_steps + 1):
                frac = k / n_steps
                lat, lng = interpolate(p1[0], p1[1], p2[0], p2[1], frac)
                # 加一点 GPS 抖动（±2m），模拟真实定位
                jitter = self.rng.uniform(-2.0, 2.0)
                lat += jitter / 111320.0
                lng += jitter / (111320.0 * math.cos(math.radians(lat)))
                run_time += self.sample_interval
                cur_ts += int(self.sample_interval * 1000)
                # 速度微调，限制在配速区间
                v = min(max(base_speed * self.rng.uniform(0.95, 1.05),
                           1000.0 / self.max_pace), 1000.0 / self.min_pace)
                acc = self.rng.uniform(3.0, 8.0)      # GPS 精度 3~8m
                sats = self.rng.randint(15, 25)       # 卫星 15~25 颗
                off_fence = 0                         # 围栏内
                track.append(self._point(idx, lat, lng, v, run_time, cur_ts, off_fence, acc, sats))
                idx += 1
        return track

    @staticmethod
    def _point(idx, lat, lng, speed, run_time, ts_ms, off_fence, acc=5.0, sats=20):
        return {
            "index": idx,
            "lat": round(lat, 6),
            "lng": round(lng, 6),
            "speed": round(speed, 2),
            "accuracy": round(acc, 1),
            "satellites": sats,
            "runTime": int(run_time),
            "collectTime": ts_ms,
            "offFenceDisM": off_fence,
            "state": 1,
        }


class RunDataSimulator:
    """一次完整阳光跑的数据模拟与上报。"""

    def __init__(self, client, run_record_code, start_entity, school_rule, common_config,
                 sport_type=1, run_scene=0):
        """
        client: SdxyClient 实例
        start_entity: startSunRun_v2 响应（含 runRecordCode/targetPoints/cheatLevel）
        school_rule: 学校规则 dict（minPace/maxPace/singleMinDistance/requiredPointCounts 等）
        common_config: 通用配置 dict（stepInterval/paceInterval/strideInterval/paceAbnormalTime）
        """
        self.c = client
        self.run_record_code = run_record_code
        self.sport_type = sport_type
        self.run_scene = run_scene
        self.rule = school_rule or {}
        self.cfg = common_config or {}
        self.track = []
        self.steps = []
        self.stride = []
        self.pass_points = []
        self.duration_s = 0
        self.distance_m = 0
        self.total_step = 0
        self.pause_count = 0
        self.pause_times = 0

    # ---- 数据生成 ----

    def generate(self, path_points, duration_s=None, distance_m=None, step_length=0.8,
                 cadence=175, start_ts_ms=None):
        """
        生成完整跑步数据。
        path_points: 关键路径点 [(lat,lng)]，须包含起点、所有打卡点、终点。
        """
        rule_min = self.rule.get("minPace", 300)      # 秒/公里，默认 5:00
        rule_max = self.rule.get("maxPace", 540)      # 秒/公里，默认 9:00
        seg_len = sum(haversine(path_points[i][0], path_points[i][1],
                                path_points[i + 1][0], path_points[i + 1][1])
                      for i in range(len(path_points) - 1))
        self.distance_m = distance_m if distance_m is not None else int(seg_len)
        # 时长按配速区间中值估算
        mid_pace = (rule_min + rule_max) / 2
        est_dur = self.distance_m / 1000.0 * mid_pace
        self.duration_s = int(duration_s if duration_s is not None else est_dur)

        # 步数与步幅自洽：步数 = 距离 / 步幅；步频 = 步数 / 时长
        self.total_step = int(self.distance_m / step_length)
        actual_cadence = self.total_step / (self.duration_s / 60.0)  # 步/分
        # 若步频超范围，调整步幅
        if actual_cadence < 150 or actual_cadence > 190:
            step_length = self.distance_m / (cadence * self.duration_s / 60.0)
            self.total_step = int(self.distance_m / step_length)

        start = start_ts_ms if start_ts_ms else int(time.time() * 1000)
        traj = RunTrajectory(path_points, self.distance_m, self.duration_s,
                             rule_min, rule_max, seed=42)
        self.track = traj.generate(start, path_points[0][0], path_points[0][1])

        # 步数区间（按 stepInterval 分片）
        step_interval = self.cfg.get("stepInterval", 30)  # 秒
        n_slices = max(1, self.duration_s // step_interval)
        steps_per_slice = self.total_step / n_slices
        acc = 0
        for i in range(n_slices):
            start_step = int(acc)
            end_step = int(acc + steps_per_slice)
            acc += steps_per_slice
            self.steps.append({
                "index": i,
                "startTime": start + i * step_interval * 1000,
                "startStep": start_step,
                "endTime": start + (i + 1) * step_interval * 1000,
                "endStep": min(end_step, self.total_step),
            })
        # 尾段补齐
        if int(acc) < self.total_step:
            self.steps[-1]["endStep"] = self.total_step

        # 步幅数据（strideInterval 分片）
        stride_interval = self.cfg.get("strideInterval", 60)
        n_stride = max(1, self.duration_s // stride_interval)
        for i in range(n_stride):
            self.stride.append({
                "index": i,
                "stride": round(step_length, 3),
                "time": stride_interval * 1000,
            })

        return self

    def mark_pass_points(self, target_points, pass_durations=None):
        """将 targetPoints 标记为已通过，clockTime 落在跑步时间窗内。"""
        self.pass_points = []
        for i, tp in enumerate(target_points):
            p = dict(tp)
            p["passStatus"] = True
            # clockTime 均匀分布在跑步过程中
            frac = (i + 1) / (len(target_points) + 1)
            p["clockTime"] = int(self.duration_s * frac * 1000)
            self.pass_points.append(p)
        return self

    # ---- 数据上报 ----

    def _sign(self, body):
        return make_sign(body, self.c.sign_key)

    def upload_track(self):
        """uploadRunRecord：上传 GPS 轨迹。"""
        body = {"runRecordCode": self.run_record_code, "pointList": self.track}
        return self.c.post_json_with_sign("run-front/run/uploadRunRecord", body)

    def upload_steps(self):
        """uploadStepsRecord：上传步数区间。"""
        body = {"runRecordCode": self.run_record_code, "stepList": self.steps}
        return self.c.post_json_with_sign("run-front/run/uploadStepsRecord", body)

    def upload_stride(self):
        """uploadStrideRecord：上传步幅。"""
        body = {"runRecordCode": self.run_record_code, "strideList": self.stride}
        return self.c.post_json_with_sign("run-front/run/uploadStrideRecord", body)

    def upload_all(self):
        results = {
            "track": self.upload_track(),
            "steps": self.upload_steps(),
            "stride": self.upload_stride(),
        }
        return results

    # ---- 结束 ----

    def build_finish_body(self):
        """按 StopRunUtils.q 构造 finishSunRun_v2 body。"""
        cfg = self.cfg
        body = {
            "runRecordCode": self.run_record_code,
            "duration": str(self.duration_s),
            "distance": str(self.distance_m),
            "totalStep": str(max(0, self.total_step)),
            "stepInterval": cfg.get("stepInterval", 30),
            "paceInterval": cfg.get("paceInterval", 60),
            "alignType": 1,               # amapGPSLevel
            "pauseCount": self.pause_count,
            "pauseTimes": str(self.pause_times),
        }
        if self.pass_points:
            body["targetPoints"] = self.pass_points
        # 正常结束：cheatList/invalidReasons 为空，status=0
        return body

    def finish(self):
        """finishSunRun_v2：结束跑。"""
        body = self.build_finish_body()
        return self.c.post_json("run-front/run/finishSunRun_v2", body, with_sign=True)

    def full_flow(self, path_points, target_points):
        """一键：生成 -> 上传 -> 结束。"""
        self.generate(path_points)
        self.mark_pass_points(target_points)
        up = self.upload_all()
        fin = self.finish()
        return {"upload": {k: (v.status_code, v.text[:200]) for k, v in up.items()},
                "finish": (fin.status_code, fin.text[:500])}


if __name__ == "__main__":
    # 演示：生成一份自洽数据（不联网）
    sim = RunDataSimulator(
        client=None, run_record_code="DEMO",
        start_entity=None,
        school_rule={"minPace": 300, "maxPace": 540, "singleMinDistance": 2000},
        common_config={"stepInterval": 30, "paceInterval": 60, "strideInterval": 60},
    )
    # 围栏内绕圈路径（4 个打卡点 + 回到起点），总长约 2km
    pts = [(36.1000, 117.1000), (36.1010, 117.1000), (36.1010, 117.1010),
           (36.1000, 117.1010), (36.1000, 117.1000)]
    sim.generate(pts, duration_s=720, distance_m=2000)
    sim.mark_pass_points([
        {"lat": 36.1005, "lng": 117.1005, "code": 1, "type": 1, "passStatus": False},
        {"lat": 36.1005, "lng": 117.1010, "code": 2, "type": 1, "passStatus": False},
    ])
    body = sim.build_finish_body()
    print(json.dumps(body, ensure_ascii=False, indent=2))
    print(f"\n轨迹点 {len(sim.track)} 个，步数 {sim.total_step}，时长 {sim.duration_s}s，距离 {sim.distance_m}m")
    print(f"平均配速 {sim.duration_s/60/(sim.distance_m/1000):.1f} min/km")
    print(f"步频 {sim.total_step/(sim.duration_s/60):.0f} 步/分，步幅 {sim.distance_m/sim.total_step:.2f} m")

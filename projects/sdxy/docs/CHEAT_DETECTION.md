# 阳光跑防作弊检测机制

> 基于反编译源码还原（`SunshineRunService` / `DataComponent` / `CheatingDetectionComponent` / `StopRunUtils` / `hp8` / `r22` / `sh1`）。开始跑 `startSunRun_v2` → 结束跑 `finishSunRun_v2` 全链路。

## 一、开始阶段（服务端下发规则）

| 字段 | 说明 |
|------|------|
| `cheatLevel` | 作弊等级 1~4，**3/4 级启用步幅异常检测**（`StartRunEntity`） |
| `whiteFlag` / `gpsWhiteFlag` | 白名单，跳过部分校验 |
| `clockMode` | 打卡模式：1=必选+可选点，2/3=目标点计数 |
| `targetPoints` | 必经点/打卡点列表（`TargetPoints`：lat/lng/code/type/passStatus/clockTime） |
| `activityInfo` | 活动规则（`activityMinPace`/`activityMaxPace`/`singleMinDistance`） |
| `SchoolRule` | 学校规则（`minPace`/`maxPace`/`singleMinDistance`/`requiredPointCounts`/`optionalPointGoalCounts`/`gpsWhiteFlag`） |
| `FaceCheckConfig` | 人脸抽检配置（`lowerLimit`~`upperLimit` 随机距离触发） |

## 二、跑步中客户端本地检测

### 虚拟定位（cheatType=110，每 30 秒轮询）

`CheatingDetectionComponent` 用 `ScheduledExecutorService.scheduleAtFixedRate(30s)` 周期调用 `sh1.b()`：

```java
// r22.a()：反射查 ServiceManager
Class.forName("android.os.ServiceManager")
    .getDeclaredMethod("getService", String.class)
    .invoke(null, "service_mock_location")  // mock 定位服务
    .invoke(null, "service_fl_ml")          // 某厂商虚拟定位服务
// 任一存在 -> CheatResult(110, "虚拟定位", time)
```

### 其他实时监控（`SunshineRunService` native 回调）

| 回调 | 监控项 |
|------|--------|
| `onGpsSignal(signalIntensity, satellites)` | GPS 信号强度 / 卫星数 |
| `enterFence` / `leaveFence` | 电子围栏进出 |
| `onCountSensorStepChange` | 计步传感器 |
| `onDurationChange` / `onPauseDurationChange` | 跑步/暂停时长 |
| `onNetworkStateChange` | 网络状态 |
| `startFaceRecognition` / `stopFaceRecognition` | 随机距离触发人脸识别 |
| `onCheatChange(Map<Integer,CheatResult>)` | 作弊检测结果回传 |

配速超范围 → `PauseTimerType.SPEED_ERROR` 暂停态；人脸识别 → `FACE_RECOGNITION` 暂停态。

### 实时配速异常表（`SunshineRunVM`，跑步中持续判定）

| 表 | 触发条件 |
|----|---------|
| 大异常表 | `当前距离 < 总距离×20%` 且速度异常 且 距上次提示 ≥200 米 |
| 小配速表 | 距离未完成 或 打卡未全 OK 或 速度异常 或 异常计时中 |

命中大异常表 → 记录 `mLastBigErrViewDis` 并进入速度异常计时；小配速表全条件满足才解除。

### GPS 前置状态检测（`StartRunUtils`）

`GpsStatus == -1`（GPS 信号丢失）且 `amapGPSLevel == 2` 时，弹 GPS 错误对话框，拒绝开始/继续跑步。

## 三、采集上传的数据

| 数据 | Bean / 接口 | 关键字段 |
|------|------------|---------|
| GPS 轨迹 | `RunLatLng` / `uploadRunRecord` | lat/lng/accuracy/speed/satellites/runTime/offFenceDisM/collectTime |
| 步数 | `IntervalStep` / `uploadStepsRecord` | startTime/startStep/endTime/endStep |
| 配速 | `uploadPaceRecord` | paceInterval |
| 步幅 | `uploadStrideRecord` | strideList/strideInterval |
| 途经点 | `uploadPassPoint` | POI 打卡 |
| 人脸记录 | `SunshineRunFaceRecord` | confidence/rate/label/faceRequestId/bodyRequestId/checkIndex/randomDistance |

## 四、结束上传（`finishSunRun_v2` body，`StopRunUtils.q` 构造）

```json
{
  "runRecordCode": "...",
  "duration": 秒,
  "distance": 米,
  "totalStep": 步,
  "stepInterval": 步频间隔,
  "paceInterval": 配速间隔,
  "targetPoints": [{lat,lng,clockTime,code,passStatus}],
  "alignType": GPS对齐级别(amapGPSLevel),
  "pauseCount": 暂停次数,
  "pauseTimes": 暂停时长,
  "cheatList": [{cheatType,remark,actionTime}],
  "status": stopStatus,
  "invalidReasons": [{invalidType,invalidDetail}],
  "faceCheckRecordList": [...],
  "abnormalCodes": [...]
}
```

### 异常结束码

| 码 | 含义 |
|----|------|
| `7003` | 正常结束标记（`StopRunUtils.h()` 返回） |
| `2072` / `2075` | 服务端异常结束（`SunshineRunService.s()`，cheatType=0 处理） |
| `2073` / `2074` | 服务端异常结束 + 数据错误（`isDataError=true`，带提示文案） |
| `abnormalCodes` | 异常结束时随 finish body 上传的异常码数组（`checkData != 0` 时） |

## 五、服务端校验规则（`hp8.e()` 生成的 `invalidReasons`）

| invalidType | 检测项 | 触发条件 |
|-------------|--------|---------|
| 25 | GPS 关闭 | `cheatType==6` |
| 58 | 分段步数-距离异常（步幅作弊） | `cheatLevel`∈{3,4} 且 `lastSegmentStepExceptionNum > segmentStrideExceptionNum` 且非白名单 |
| 2 | 距离未达标 | `distance < singleMinDistance` |
| 1 | 打卡点未完成 | `clockMode==1`：必需点/可选点不足；`clockMode∈{2,3}`：通过点 < 要求 |
| 3 | 配速过快/过慢 | 平均配速 < `minPace` 或 > `maxPace` |
| 53 | 配速持续异常 | 异常持续 > `paceAbnormalTime` 秒 |

配速计算：`pace = distance / duration * 1000`（`hp8.a()`）。

## 六、服务端返回判定（`FinishRunResult`）

| 字段 | 含义 |
|------|------|
| `status` | 成绩有效/无效 |
| `validDistance` | 扣除无效段后的有效距离 |
| `appealFlag` | 是否可申诉 |
| `recheckStatus` | 人工复核状态（人脸存疑 → 1~3 个工作日） |
| `alertTip` | 警告提示 |
| `rewardDistance`/`rewardTimes` | 奖励 |

## 七、恢复跑步检测（断点续跑 `queryUnFinishRun`）

| 码 | 含义 |
|----|------|
| `7001` | 本地跑步记录缺失 → "系统未找到本次跑步记录数据，无法为您恢复跑步" |
| `7002` | 跑步数据异常 → "系统检测跑步数据异常，无法为您恢复跑步" |

两种情况都强制"结束跑步"，不允许继续。

## 八、环境检测（明确结论）

跑步模块**不检测 Root / Frida / Xposed / 模拟器 / 多开**。全项目 grep `isRoot/isFrida/isXposed/isEmulator/模拟器` 均无结果。

环境检测只可能出现在**外围风控 SDK**（阿里实人认证、极验等第三方，仅在开启人脸认证时顺带触发）或**服务端设备指纹**层面。因此：

- 纯模拟跑步数据：无需伪装环境，直接构造自洽数据即可。
- 开人脸认证时：阿里实人 SDK 会顺带做环境/活体检测。

## 九、风控结论

客户端本地只做 **虚拟定位 + 围栏 + 配速（含实时异常表）+ 人脸 + GPS 信号** 的实时拦截（作弊检测每 30 秒才跑一次，检测面有限）。**真正防作弊在服务端**：用上传的 GPS 轨迹、步数、步频、配速、步幅做交叉校验——距离是否达标、步数-距离是否匹配、配速是否在规则内、打卡点是否经过、人脸置信度是否合格；异常则扣减 `validDistance`、标无效或转人工复核。

## 十、绕过要点（模拟实现需保证数据自洽）

1. 轨迹点连续、速度/加速度无跳变，落在围栏内，`accuracy`/`satellites` 合理（如 3~8m / 15~25 颗）。
2. 距离 ≥ 要求值，配速落在 `minPace~maxPace` 内；实时配速无超过 20% 距离的持续异常段。
3. 步数 = 距离 / 步幅（步幅 0.6~1.2m），步频 = 步数 / 时长（150~190 步/分），分段步数无异常突变。
4. 所有 `targetPoints` 的 `passStatus=true`，`clockTime` 落在跑步时间窗口内。
5. 不注入 mock 定位（`service_mock_location`/`service_fl_ml` 必须不存在），GPS 信号正常。
6. `cheatList` 为空、`invalidReasons` 为空，`status` 正常。
7. 无需伪装环境（Root/Frida/模拟器检测不存在）；但开人脸认证时需真实人脸，纯数据伪造过不了阿里实人比对。

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

## 八、环境检测（结论已修正：客户端不检测 ≠ 整体不检测）

### 8.1 客户端 Java 层（跑步模块自身）

跑步模块 Java 代码**不检测 Root / Frida / Xposed / 模拟器 / 多开**。全项目 grep `isRoot/isFrida/isXposed/isEmulator/模拟器` 均无结果。

### 8.2 但官方使用指南明确声明检测（★重要修正）

官方《闪动校园使用指南》「注意事项」第 ⑤ 条原文：

> 安卓用户特别注意：手机中若装有 **root 刷机、xposed 模拟器、抢红包软件、游戏外挂**等，
> 跑步前必须卸载，否则触发防作弊、无法跑步成功，有封号风险。

据此修正结论：环境检测**真实存在**，但不在客户端 Java 层，而在以下三处：

| 检测层 | 位置 | 说明 |
|--------|------|------|
| **易盾加固壳** | `libNetHTProtect.so`（native） | 反调试/反 Xposed/反 Frida，Java grep 覆盖不到 |
| **服务端设备指纹** | 阿里实人风控 `libkcbw/lywm/zj*AliAgainstId.so` | android_id/OAID/IMEI/MAC + 环境指纹 |
| **外围风控 SDK** | 阿里实人认证、极验 | 开人脸认证时顺带做环境/活体检测 |

**结论**：
- 纯协议模拟（不装 Xposed/Frida，干净环境）→ 客户端检测面为 0，主要风险在服务端设备指纹。
- 用 LSPosed/Frida 动态 hook 采集 → **必须靠 Shamiko 隐藏 root/Zygisk + HideMyApplist 隐藏模块**，否则撞官方点名的「xposed」检测。
- 开人脸认证时：阿里实人 SDK 会做活体+环境检测，纯数据伪造过不了。

## 八-2、业务规则风控（官方指南披露的 5 种高层防作弊）

> 来源：官方《使用指南》「注意事项」第 ④ 条。这些是**跨设备/跨账号/跨会话**的行为画像风控，
> 不在单次跑步数据校验（§五 hp8.e）范围内，属 `risk-control-adversary` 的「业务规则风控」维度。

| 防作弊项 | 检测原理（推测） | 对应数据特征 | 我之前的覆盖 |
|---------|----------------|-------------|------------|
| **代跑识别** | 账号↔设备↔地理位置绑定 | 同账号频繁换设备/异地跑步 | ❌ 未分析 |
| **接力跑** | 轨迹/步频/步幅的多人体征 | 中途步频步幅指纹突变（换人） | ❌ 未分析 |
| **骑车摇手机** | 速度 + 步频异常的组合特征 | 配速过快（车）+ 步频异常高（摇） | ⚠️ 仅配速（invalidType 3） |
| **一人多机** | 设备指纹（android_id/OAID/IMEI/MAC）与账号绑定 | 多设备同时在线同账号 | ❌ 未分析 |
| **软件多登** | 会话管理（token/satoken） | 同账号多端 token 并存 | ❌ 未分析 |

> 这些检测逻辑不在客户端 Java（已确认），极可能在**服务端风控平台**（配合 §八 的阿里实人风控指纹）。
> 对抗思路：单设备单账号单会话自洽（`risk-control-adversary` 主线），不横向复用账号/设备。

## 八-3、学校规则完整维度（时段/频次/上限，之前只列了配速步幅）

> 来源：官方《使用指南》「学校规则」。这些是 `SchoolRule`/`CommonConfig` 的完整校验维度，
> 服务端据此判定跑步是否**有效**（无效 ≠ 作弊，但成绩作废）。

| 规则维度 | 示例值 | 我之前的覆盖 |
|---------|--------|------------|
| 跑步**日期窗口** | 学期内（如 2023/3/13–5/19） | ❌ 漏 |
| 跑步**时段** | 周一至周日 6:00–22:30 | ❌ 漏 |
| 单次**最低/最高公里数** | 最低 1km、最高 8km | ⚠️ 仅 singleMinDistance |
| **每天公里数上限** | 10km/天 | ❌ 漏 |
| **每天次数上限** | 2 次有效/天 | ❌ 漏 |
| **每周次数上限** | 4–14 次 | ❌ 漏 |
| **暂停时长/次数** | 倒计时内必须继续跑，否则自动结束无效 | ❌ 漏 |
| 配速/步幅/打卡点 | 已分析（§五 hp8.e） | ✅ |

## 八-4、学生卡认证（所有功能的前提）

官方指南明确：**必须先完成学生卡认证**，否则无法使用阳光跑/活动跑/AI运动/排行榜/校园应用。

认证链路（推测对应接口）：
1. 选学校 → 输学号 → 下一步
2. 核对姓名/性别/年级/校区/班级 → 提交认证

> 与动态实测吻合：当前账号 `studentNumber` 空（未认证）→ 阳光跑接口返回 `code=1503`。
> 未认证账号可调用只读接口（用户信息/学期/围栏），但**无法发起跑步**。

## 八-5、未分析的功能模块（后续如需再补）

| 模块 | 状态 |
|------|------|
| AI 运动（AI 骨骼识别 + 作业/自由模式） | ❌ 完全未分析 |
| 活动跑（奖励翻倍：次数×1.2/里程×1.7） | ⚠️ 仅 sportType 分支 |
| 自由跑（sportType=2，不计入阳光跑） | ⚠️ 仅 sportType 分支 |
| 课程考勤/选课/体测/理论考试 | ❌ 完全未分析（非跑步核心） |

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

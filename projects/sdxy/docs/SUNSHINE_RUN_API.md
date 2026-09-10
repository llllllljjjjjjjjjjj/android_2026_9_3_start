# sdxy 阳光跑（Sunshine Run）接口清单

> 目标：闪动校园（`com.huachenjie.shandong_school` v8.6.8），BaseUrl `https://api.huachenjie.com/`
> 阳光跑 = 首页「运动」tab 下的阳光跑/阳光体育模块，属学校跑操/打卡类核心功能。
> 本文档为**接口静态清单**（源自反编译 `ISunshineApi`/`IRunApi`/`IFreeApi`），含参数说明与调用链顺序。**未做任何写操作实测**（只读查询曾 `code=0` 验证会话可用）。
> 通用传输层（header `app/api/v/pv/e`、`sign`、字段加密、`Authorization`+`satoken` 注入）见 `docs/LOGIN_API.md` §2，会话与密钥见 `artifacts/session.json`。

---

## 0. 重要提示（先读）

- **本模块多为「写操作」**（开始/上传/结束跑、申诉、弹幕、提交信用分），随意调用会**真实产生跑步记录 / 触发风控**。除只读查询外，**先与小号/测试数据 + 完整签名指纹**再动。
- 只读（建议先调、风险低）：`plan/selectList`、`querySchoolRunSummary`、`querySunRunAbstractInfoV2`、`pageSunRunRecord`、`queryUnFinishRun`、`runRecordDetail`、`queryRunRecordCount`、`stadiumDeductionList`、`listUserReward`、排行榜、徽章、弹幕获取。
- 写操作（谨慎）：`startSunRun_v2`、`checkSunRunConfig`、`uploadRunRecord`/`uploadStepsRecord`/`uploadPaceRecord`/`uploadStrideRecord`/`uploadPassPoint`、`finishSunRun_v2`、`abnormalFinishSunRun`、`resume`、`appealRunRecord`、`sendBarrage`、`creditBook/submit`。
- 敏感字段（`password`/`phone`/`schoolName`/`userName`/`studentNumber` 等）值由 EncryptInterceptor 加密；响应中这些字段也是 AES 密文，需 `sdxy_crypto.decrypt_field` 解。

---

## 1. 阳光跑核心调用链（进入 → 开始 → 结束）

```
① 学期/计划         run-front/account/semesterSelector        {semesterCode×?}    -> semesterCode=13(2026-2027第一学期)
② 跑步计划列表       run-front/run/plan/selectList            {semesterCode}      -> RunPlanListBean{list[runPlanCode,...]}
③ 进入阳光跑摘要     run-front/run/querySunRunAbstractInfoV2   {semesterCode, runPlanCode, sportType}
④ 学校围栏           run-front/school/querySchoolFences        {schoolCode}       -> GeoFenceDetail[]{fenceCode,中心坐标,规则}
⑤ 检查配置          run-front/run/checkSunRunConfig           {schoolCode, subSchoolCode, targetDistance,
                                                               activityCode, runPlanCode, fenceCode, sportType}
⑥ 开始跑步          run-front/run/startSunRun_v2               {schoolCode, fenceCode, activityCode, lat, lng,
                                                               targetDistance, useCreditSword, runPlanCode, sportType}
                                                               -> StartRunEntity{runRecordCode, targetPoints[], rules}
⑦ 跑中上报(周期循环) uploadRunRecord(轨迹,带sign) / uploadStepsRecord(步数) /
                     uploadPaceRecord(配速) / uploadStrideRecord(步幅) / uploadPassPoint(打卡点)
⑧ 结束跑步          run-front/run/finishSunRun_v2              (JSON body, 详见 SUNSHINE_RUN_DATA_FORMAT.md)
  异常结束          run-front/run/abnormalFinishSunRun
```

---

## 2. 接口全集

### 2.1 ISunshineApi（阳光跑主入口 `com.huachenjie.running.api.ISunshineApi`）

| 接口（`run-front/…`） | 方法 | 请求形态 | 参数 |
|---|---|---|---|
| `run/querySchoolRunSummary` | B | Form `{time}` | 学校跑量汇总（totalDistance/runningUserList/tipMsg） |
| `run/getDefaultBarrage` | C | POST 无参 | 默认弹幕 |
| `run/getLatestBarrage` | v | POST 无参 | 最新弹幕 |
| `run/sendBarrage` | h | Form `{content}` | 发弹幕（写） |
| `run/queryUnFinishRun` | a | Form `{sportType…}` | 断点续查（只读） |
| `run/plan/selectList` | j | Form `{semesterCode}` | 跑步计划列表（只读） |
| `run/querySunRunAbstractInfoV2` | k | Form `{semesterCode, runPlanCode, sportType}` | 进入阳光跑页摘要（只读） |
| `run/checkSunRunConfig` | m | Form `{schoolCode, subSchoolCode, targetDistance, activityCode, runPlanCode, fenceCode, sportType}` | 开始前配置检查 |
| `run/startSunRun_v2` | e | Form `{schoolCode, fenceCode, activityCode, lat, lng, targetDistance, useCreditSword, runPlanCode, sportType}` | 开始跑步（写） |
| `run/finishFreeRun` | b | JSON Body | 结束自由跑 |
| `run/abnormalFinishSunRun` | c | JSON Body | 异常结束阳光跑 |
| `run/abnormalFinishActivityRun` | G | JSON Body | 异常结束活动跑 |
| `run/stadiumDeductionList` | g | Form `{pageSize, pageNum, runPlanCode}` | 操场扣减记录（只读） |
| `run/listUserReward` | o | Form `{pageSize,pageNum,semesterCode,runPlanCode,type}` | 奖励列表 |
| `run/appealRunRecord` | s | Form `{runRecordCode, problemContent, semesterCode}` | 申诉记录（写） |
| `run/resume` | u | Form `{sportType, runRecordCode}` | 续跑 |
| `run/pageSunRunRecord` | z | Form `{pageSize, pageNum, semesterCode, runPlanCode}` | 记录分页（只读） |
| `school/querySchoolFences` | I | Form `{schoolCode}` | 学校围栏（只读） |
| `school/filterSchoolActivityFence` | d | Form `{activityFenceCode}` | 活动围栏过滤 |
| `school/filterUsableFence` | E | JSON Body | 可用围栏过滤 |
| `rank/runProgress` | A | Form `{sex, scope, runPlanCode}` | 跑步进度排行 |
| `rank/distance` | q | Form `{sex, scope, rankCycle, type, runPlanCode}` | 距离排行 |
| `api/run/medal/getRankings` | r | Form `{sex, runPlanCode}` | 徽章排行 |
| `api/run/medal/getMedalNum` | x | Form `{runPlanCode}` | 徽章数 |
| `creditBook/submit` | H | Form `{runRecordCode, declaration}` | 提交信用分声明（写） |
| `creditBook/pageCreditBookRunRecord` | l | Form `{pageSize, pageNum}` | 信用分记录 |
| `creditBook/message/list` | n | Form `{pageSize, pageNum}` | 信用书消息 |
| `creditBook/notes` | p | POST 无参 | 信用书备注 |
| `task/getDescription` | i | POST 无参 | 任务说明 |
| `common/runVideo` | J | Form `{time}` | 跑步视频 |
| `api/mall/basic/banner/runFinish` | F | POST 无参 | 跑完横幅 |
| `api/huawei/health/deduction/summary` / `records` | D / f | Form `{runPlanCode}` / `{pageSize,pageNum,runPlanCode}` | 穿戴设备扣减 |
| `activity/activityList` | w | Form `{currentSemester}` | 活动列表 |
| `activity/activityDetail` | y | Form `{sunRunActivityCode}` | 活动详情 |
| `ai/aiRecordDetail` | t | Form `{pageSize, pageNum, runPlanCode}` | AI 跑步记录 |

### 2.2 IRunApi（实时上报 `com.huachenjie.running.api.IRunApi`）

| 接口 | 方法 | 请求形态 | 说明 |
|---|---|---|---|
| `run/queryUnFinishRun` | a | FMap | 断点（只读） |
| `run/startFreeRun` | c | FMap | 自由跑开始 |
| `run/finishFreeRun` | b | JSON Body | 自由跑结束 |
| `run/uploadPaceRecord` | d | JSON Body | 配速上报 |
| `run/uploadPassPoint` | e | JSON Body | 打卡点上报 |
| `run/uploadStrideRecord` | g | JSON Body | 步幅上报 |
| `run/uploadRunRecord` | h | JSON Body + **header `sign`** | 轨迹上报（**显式带 sign**） |
| `run/uploadStepsRecord` | j | JSON Body | 步数上报 |
| `run/finishSunRun_v2` | i | JSON Body | **结束阳光跑**（返回 FinishRunResult） |
| `run/queryRunRecordCount` | f | Form `{timeType, sportType}` | 记录数（只读） |
| `run/runRecordDetail` | k | Form `{runRecordCode, semesterCode}` | 记录详情（只读） |

> `uploadRunRecord`/`finishSunRun_v2` 的 body 构造与 `sign`（`qf7.j` 经 `c23.d()`）在 `docs/CORE_CLASSES_ANALYSIS.md` §三 + `scripts/sdxy_run_simulator.py` 已有完整实现（sunshine run 全链路已实测 `code=0`）。

### 2.3 IFreeApi（自由跑 `com.huachenjie.running.api.IFreeApi`）

| 接口 | 说明 |
|---|---|
| `run/free/detail` | 自由跑详情（BaseApi） |
| `run/startFreeRun` / `finishFreeRun` | 开始/结束自由跑 |
| `run/pageFreeRunRecordList` | 自由跑记录分页 |
| `run/queryRunRecordCount` | 记录数 |

---

## 3. 会话/鉴权（复用 `artifacts/session.json`）

所有接口需 `Authorization`(token JWT) + `satoken`(UUID) + 动态 `sign`。用 `SdxyClient` 已封装：

```python
import json
from scripts.simulate_sunshine_run import SdxyClient
s = json.load(open("projects/sdxy/artifacts/session.json", encoding="utf-8"))
c = SdxyClient(base_url="https://api.huachenjie.com/",
               token=s["token"], satoken=s["satoken"], sign_key="F44B0282BEA83557")
c.session.trust_env = False

# 只读示例（已实测 code=0）
c.query_sun_run_abstract(semester_code="13", run_plan_code="<plan>", sport_type=1)
c.query_unfinish_run(sport_type=1)
```

> token 有效期到 2026-11-06（JWT `exp`）；过期/被踢（code 1005/1503/1504）用 `login_full.py` 全自动重新登录。

---

## 4. 备注

- 写操作前建议先用**只读查询**探明 `runPlanCode`/`fenceCode`/`activityCode`（来自 `plan/selectList`、`querySchoolFences`、`activity/activityList`），避免盲调。
- 阳光跑 **数据传输/风控**需符合 `CHEAT_DETECTION.md`（轨迹/配速/步幅/打卡点规则），否则被判无效；`finishSunRun_v2` 涉及 `runImgRecord`（图片派生 native `K.b2s`，见 `docs/REVERSE_REPORT.md` §4）。

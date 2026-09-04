# sdxy（闪动校园）风控对抗方案

> 生成日期: 2026-09-04 | 平台: Android | 资料基线: projects/sdxy/docs/（REVERSE_REPORT / CHEAT_DETECTION / FIELD_TEST_LOG / SIMULATION）+ 真机实测 | 知识库: L1 现有 E-26/F-03 | 动态优先级: **行为+数据自洽优先**（签名已破，非瓶颈）

## 〇、分级方案（双维度）

| 版本 | 风险定位 | 成本 | 节奏区间 | 账号/设备投入 | 预期效果 |
|------|---------|------|---------|--------------|---------|
| 保守版 | 低风险 | 低 | 单次跑步按真实时长（不加速） | 单账号+单真机+固定IP | 存活优先，数据一次成型 |
| 平衡版 | 中风险 | 中 | 单次跑步时长可压缩到规则下限 | 少量账号轮换+真机 | 均衡 |
| 激进版 | 高风险 | 高 | 贴规则下限+批量跑 | 账号池+设备池+住宅IP | 吞吐优先，但本平台强风控，不推荐 |

> ⚠️ 本平台已实测触发**账号级封禁 + 设备指纹关联**，激进版（批量/多开/多设备）大概率触发 GNN 关联图谱（E-25），**强烈建议只走保守/平衡版**。

## 一、接口总览

| 接口ID | 端点 | 方法 | 业务含义 | 签名 | 参数加密 | 频率特征 | 环境检测 | 业务风控 |
|---|---|---|---|---|---|---|---|---|
| IF-01 | run-front/account/queryCommonUserInfo | POST | 用户信息 | 有 | 无 | 低频 | 无 | 登录态 |
| IF-02 | run-front/attend/semesterSelector | POST | 学期选择 | 有 | 无 | 低频 | 无 | - |
| IF-03 | run-front/school/querySchoolFences | POST | 围栏查询 | 有 | 无 | 低频 | 无 | - |
| IF-04 | run-front/run/checkSunRunConfig | POST | 跑步配置 | 有 | 无 | 低频 | 无 | 未完成跑步校验(2070) |
| IF-05 | run-front/run/startSunRun_v2 | POST | 开始跑 | 有 | 无 | 低频 | 无 | **大数据风控(2999)** |
| IF-06 | run-front/run/uploadRunRecord | POST | 轨迹上传 | 有 | 无 | 跑步中周期 | 无 | 数据校验 |
| IF-07 | run-front/run/uploadStepsRecord | POST | 步数上传 | 有 | 无 | 跑步中周期 | 无 | 数据校验 |
| IF-08 | run-front/run/uploadStrideRecord | POST | 步幅上传 | 有 | 无 | 跑步中周期 | 无 | **步幅校验(请合规跑步)** |
| IF-09 | run-front/run/finishSunRun_v2 | POST | 结束跑 | 有 | 无 | 单次 | 无 | 数据校验+风控 |
| IF-10 | run-front/run/abnormalFinishSunRun | POST | 异常结束 | 有 | 无 | 低频 | 无 | - |
| IF-11 | run-front/run/queryUnFinishRun | POST | 未完成查询 | 有 | 无 | 低频 | 无 | - |

## 二、逐接口风控分析（核心接口）

### IF-05 startSunRun_v2（开始跑，风控第一道闸）

**请求特征**：POST，参数 schoolCode/fenceCode/activityCode/lat/lng/targetDistance/useCreditSword/runPlanCode/sportType + 公共参数 + sign。

**风控点（六维）**

| 维度 | 检测机制 | 证据等级 | 置信度 | 证据 |
|---|---|---|---|---|
| 业务规则风控 | 大数据风控平台按 userId/学号查封禁记录 | **已实证** | 高 | 实测 code=2999「阳光跑功能已被系统禁用」 |
| 设备指纹 | deviceId(android_id)+OAID+IMEI+MAC+阿里实人风控ID 关联 | 已实证 | 高 | 反编译 xta/ie/y7/jl2 采集点 |
| 签名校验 | AES-256-CBC+SHA256 旋转+Base64 | 已实证 | 高 | 算法已离线还原，密钥确定 |

**对抗手段**

| 风控点 | 手段 | 优先级 |
|---|---|---|
| 业务规则风控 | 换未被封的学号+设备，数据一次合规 | P0 |
| 设备指纹 | 真机保真，不伪造（硬件级不可伪造，E-20） | P0 |
| 签名 | 离线算法（sdxy_crypto.py），无需 oracle | P2 |

**失败模式**：账号被封后 startSunRun_v2 直接 2999；换设备同学号无效（账号级封禁）；换号同设备被设备指纹关联（F-05）。

### IF-06/07/08 上传接口（数据自洽是核心）

**风控点**

| 维度 | 检测机制 | 证据等级 | 置信度 | 证据 |
|---|---|---|---|---|
| 参数完整性 | 缺公共参数报 1002「请求时间/设备类型/设备唯一标识不能为空」 | 已实证 | 高 | 实测 |
| 数据校验 | 步幅格式不合规报「请合规跑步」 | 已实证 | 高 | 实测 |
| 行为画像 | 轨迹/步数/步频/配速/步幅交叉校验，异常累积判作弊 | 已实证 | 高 | 实测触发封禁 |

**对抗手段**：数据一次成型、完全自洽（见 §四请求策略），不留异常记录。

## 三、全局风控面（跨接口）

### 风控分层处置（本平台核心特征，已实证）

| 层 | 触发接口 | 表现 | 本质 |
|---|---|---|---|
| 硬拦截 | startSunRun_v2 | code=2999「功能被禁用」 | 明确封禁 |
| 软降级 | 校园跑摘要查询 | `validStatus=false` →「本学期还未开始」 | 封禁伪装成"未开放" |
| 连带吊销 | 任意请求 | code=1503「登录状态已失效」 | token 被吊销 |

**关键结论**：封禁是**账号级 + 设备指纹关联**。"本学期还未开始"是柔性降级伪装（`StartRunUtils.N()` 里 `!isValidStatus()` 弹 `out_of_semester_prompt`），不是真实学期判断——学期明明已开始（semesterCode=13，startTime 2026-07-29 < 当前）。

### 设备指纹采集面（E-05 适配）

| 指纹 | 采集点 | 可伪造性 |
|---|---|---|
| android_id | jl2/q40/y7 | 中（Root 可改，但需重装 App） |
| OAID | 多厂商 OAID SDK | 中（可重置） |
| IMEI/MAC | y7 getImei/getMacAddress | 低（硬件级） |
| 阿里实人风控 ID | libkcbw/lywm/zj*AliAgainstId.so | **不可伪造**（E-20 硬件级） |

### 环境检测（弱）

跑步模块**无** Root/Frida/Xposed/模拟器检测。但广告 SDK（innotech）有作弊应用黑名单（含 magisk/fakeloc/mockloc/xposed 等包名）。纯数据模拟无需伪装环境；开人脸认证时阿里实人才顺带环境检测。

## 四、请求策略与真人模拟（核心，P0）

### 数据自洽（本次封禁的直接教训）

模拟跑步必须一次成型、六维数据全对齐，禁止反复试错累积异常：

1. **轨迹**：GPS 点连续、速度/加速度无跳变、落在围栏内、`accuracy` 3~8m、`satellites` 15~25、采样 2s。
2. **步数**：`totalStep = distance / stride`（步幅 0.6~1.2m）。
3. **步频**：`cadence = step / duration` 落在 150~190 步/分（超范围自动调步幅）。
4. **配速**：`pace = distance/duration` 落在 `minPace~maxPace`（300~540 s/km），实时无持续异常段（>20% 距离）。
5. **打卡点**：`passStatus=true`，`clockTime` 落在跑步时间窗内。
6. **步幅格式**：`uploadStrideRecord` 的 body 必须符合真实结构（**待逆向补齐**，此前报「请合规跑步」）。
7. **时间戳**：`timestamp` 与跑步开始/时长对齐，公共参数全带。

### 参数完整性（已实证的必带项）

- 公共参数 9 项：`appVersion/buildVersion/appCode/deviceId/platform/modelName/systemVersion/channel/timestamp`，缺一报 1002。
- sign = `AES(SHA256_rotate(JSON(参数+公共参数)), key)`，基于**装饰后**参数计算。
- 敏感字段（phone/password/userName/schoolName/studentNumber）AES 加密。

### 逆向期（风险最小化）

| 风险动作 | 风控后果 | 规避策略 |
|---|---|---|
| 反复试错上传 | 异常记录累积 → 封禁 | 数据先离线验证自洽，再一次性上传 |
| 缺参数直发 | 1002 异常记录 | 参数完整性清单核对后再发 |
| 残留未完成跑步 | 2070 阻塞 + 异常记录 | 开始前先 `abnormalFinishSunRun` 清理 |

### 数据期（长期策略）

- 节奏：单次跑步按真实时长（保守）或规则下限（平衡），不批量并发。
- 序列：querySchoolFences → checkSunRunConfig → startSunRun_v2 → 上传 → finishSunRun_v2，严格按序。
- 会话：token 有效期约 2 个月（JWT exp），失效后重新提取（真机 MMKV 解密）。
- 账号-设备绑定：1 学号 : 1 设备 : 1 IP，严格不交叉（E-25 去关联）。
- 人脸：`faceAuth=false` 才可纯数据模拟；`true` 时阿里实人比对无法伪造。
- **差异化变异**：轨迹抖动、配速微调、步幅浮动注入随机因子，避免统一指纹。

## 五、对抗策略优先级

| 优先级 | 项 | 状态 | 止损条件 |
|---|---|---|---|
| P0 | 数据自洽 + 一次成型 | 待补步幅格式 | 再次「请合规跑步」→ 停，逆向真实格式 |
| P0 | 换号+换设备（当前号已封） | 待用户提供 | 新号再 2999 → 设备指纹已污染，弃设备 |
| P1 | 步幅格式逆向 | 待做 | - |
| P2 | 签名/加密 | **已破** | - |

## 六、验证记录

| 日期 | 验证项 | 手段 | 结果 | 证据路径 |
|---|---|---|---|---|
| 2026-09-04 | 全链路接口打通 | dorm_run.py 实测 | ✅ 登录态/学期/围栏/配置/开始跑均通 | FIELD_TEST_LOG.md |
| 2026-09-04 | 上传/结束 | dorm_run.py 实测 | ❌ 缺公共参数+步幅格式错 | FIELD_TEST_LOG.md |
| 2026-09-04 | 风控封禁触发 | startSunRun_v2 实测 | ❌ code=2999 账号封禁 | FIELD_TEST_LOG.md |

## 七、泛化经验提炼

本次沉淀：
- **F-04** 跑步数据不自洽累积触发大数据风控封禁（致命）
- **F-05** 账号级封禁+设备指纹关联，换设备无效（严重）
- **E-27** 风控柔性降级伪装识别（"未开始"=封禁）

详见 general-principles.md 对应条目。

# 阳光跑数据格式与检测逻辑完整静态分析

> 纯静态分析（未发包、未验证）。数据来源：反编译产物 `com/zj/widget/qf7.java`、`com/huachenjie/running/bean/*`、`com/huachenjie/running/service/*`、`com/zj/widget/a15.java`。
> 关联文档：CHEAT_DETECTION.md（检测机制）、FIELD_TEST_LOG.md（实测记录）、risk-control-plan.md（风控方案）。

## 一、上传接口完整 body 格式（`qf7.java` 权威来源）

| 接口 | 方法 | body 结构 | 关键点 |
|------|------|----------|--------|
| `uploadPaceRecord` | `qf7.h` | `{"paceList":[IntervalPace],"paceInterval":long,"runRecordCode":str}` | `WriteMapNullValue` 序列化 |
| `uploadRunRecord` | `qf7.j` | `{"pois":[RunLatLng],"runRecordCode":str}` + 公共参数 + sign | sign 基于**装饰后** JSON |
| `uploadStepsRecord` | `qf7.k` | `{"stepList":[IntervalStep],"stepInterval":long,"runRecordCode":str}` | - |
| `uploadStrideRecord` | `qf7.l` | `{"strideList":[ {strideMap} ],"strideInterval":int,"runRecordCode":str}` | ⚠️ **strideMap 外包一层数组** |
| `uploadPassPoint` | `qf7.m` | `{"runRecordCode":str,"targetPoints":[TargetPoints]}` | ⚠️ **传打卡点，非 GPS 点** |
| `finishSunRun_v2` | `qf7.c` | 先 `mp8.f` 加 `runImgRecord`+`timestamp`，再 JSON | 见 §四 |

### 关键坑（此前实测踩雷的根因）

1. **stride 格式**：`strideList` 是 `[{map}]`（Map 外包一层 ArrayList），不是扁平数组。此前传扁平结构 → 服务端报「请合规跑步」。
2. **passPoint 传的是 targetPoints（打卡点）**，不是 GPS 途经点——打卡点 `TargetPoints` 只有 `lat/lng/clockTime/code/passStatus` 参与序列化。
3. **uploadRunRecord 的 sign**：基于 `JSON.toJSONString(map, WriteMapNullValue)`（装饰公共参数后）算 `cq.c(h58.c(json), c23.d())`。

## 二、数据结构全字段

### RunLatLng（轨迹点，uploadRunRecord 的 pois 元素）

序列化字段：`index`(id)、`lat`、`lng`、`offFenceDisM`、`runTime`(runTimestamp)、`state`、`collectTime`(timestamp)。非序列化：`accuracy`、`speed`、`satellites`（toString 里有，但 @JSONField 未标 name，默认参与序列化需核对——静态按字段名参与）。

> 建议模拟时带上 `accuracy`(3~8m)、`speed`、`satellites`(15~25)，与真实 GPS 采集一致。

### IntervalStep（步数区间，uploadStepsRecord 的 stepList 元素）

序列化字段：`index`(id)、`startTime`、`startStep`、`endTime`、`endStep`、`time`、`step`。非序列化：`runCode`、`isValid`、`isUploaded`。

关系：`time = endTime - startTime`，`step = endStep - startStep`。

### IntervalPace（配速区间，uploadPaceRecord 的 paceList 元素）

序列化字段：`index`(id)、`startTime`、`endTime`、`startDistance`、`endDistance`、`startStepCount`、`endStepCount`、`time`、`distance`、`stepCount`。

关系：`time = endTime - startTime`，`distance = endDistance - startDistance`，`stepCount = endStepCount - startStepCount`。

### TargetPoints（打卡点，uploadPassPoint 的 targetPoints 元素 + finish）

`@JSONType(includes={"lat","lng","clockTime","code","passStatus"})` —— **仅这 5 个字段序列化**。type/pointName/simpleName/sort/isClosingStatus/isInFence/isSensitiveFenceAdded 均 `serialize=false`。

### RunningDataV2（跑步数据，步幅检测核心）

步幅异常检测关键字段：`lastSegmentStepIndex`、`lastSegmentStrideDistance`、`lastSegmentStep`、`lastSegmentStepTime`、`lastSegmentStepExceptionNum`、`gpsAbnormalTimes`。

## 三、步幅异常检测（服务端校验，`hp8.e()`）

| 检测项 | 条件 | invalidType |
|--------|------|-------------|
| 分段步数-距离异常 | `cheatLevel∈{3,4}` 且 `lastSegmentStepExceptionNum > segmentStrideExceptionNum` 且非白名单 | 58 |

步幅规则来自 `SchoolRule`：`segmentStrideAvg`（平均步幅）、`segmentStrideExceptionNum`（允许的异常数）。

> strideMap 内部 key 在 native 层（DataComponent 大量 native 方法），Java 反编译不可见，标注**未知**。但上传格式（`strideList:[{map}]` + `strideInterval` + `runRecordCode`）已确认。

## 四、finishSunRun_v2 完整 body

### 构造链（`StopRunUtils.q` + `qf7.c` + `mp8.f`）

```
1. StopRunUtils.q 组装基础字段（见 CHEAT_DETECTION.md §四）
2. mp8.f(params)：若含 runRecordCode，追加：
   - runImgRecord = MD5(runRecordCode + "260826158.6.8" + 图片MD5 + timestamp)
   - timestamp = 当前毫秒 + 服务端时间偏移
3. qf7.c → d().i(finishSunRun_v2)
```

### runImgRecord 算法（`a15` + `mp8.f`）

```
runImgRecord = MD5( runRecordCode
                  + "260826158.6.8"
                  + k14.a.c(context, R.drawable.hcj_bg_run_index)   // 图片像素派生
                  + timestamp )

a15.c/d = 标准 MD5，hex 用 0-9a-f 字符集
k14.a.c = BitmapFactory.decodeResource(hcj_bg_run_index) → 图片像素 → K.b2s(像素, mode)
```

> `hcj_bg_run_index` 图片派生值：与 sign key 的 `bg_contact_list` 类似机制，但这是**不同的图片**（hcj_bg_run_index vs bg_contact_list）。若图片解码为 null 或 K.b2s 未解析，此值未知，runImgRecord 无法离线精确还原——需静态进一步逆向 `K.b2s`（native）或该图片资源。

### finish 完整字段（`StopRunUtils.q` 确认）

```
runRecordCode, duration(秒), distance(米), totalStep,
stepInterval, paceInterval, targetPoints(打卡点),
alignType(amapGPSLevel), pauseCount, pauseTimes,
cheatList(作弊列表), status(stopStatus),
invalidReasons(无效原因), faceCheckRecordList(人脸，runScene==20&&faceAuth),
abnormalCodes(异常码), runImgRecord(图片记录), timestamp
```

## 五、最稳妥的合规跑数据基准（静态推导，待实测）

以下参数满足「一次成型、完全自洽」的保守底线：

| 维度 | 合规值 | 依据 |
|------|--------|------|
| 距离 | ≥ 围栏 distance（如 2000m） | hp8 invalidType 2 |
| 配速 | minPace~maxPace（如 300~540 s/km） | hp8 invalidType 3 |
| 步幅 | 0.6~1.2m，分段无异常突变 | hp8 invalidType 58 |
| 步频 | 150~190 步/分 | 生理合理区间 |
| 打卡点 | passStatus=true，clockTime 在跑步窗口 | hp8 invalidType 1 |
| 轨迹 | 连续、围栏内、accuracy 3~8m、satellites 15~25 | 数据自洽 |
| cheatList | 空 | 无作弊 |
| invalidReasons | 空 | 无无效 |

## 六、native 层待补齐项（SO 分析结论）

### 已闭环（本次静态分析）

1. **sign key 图片派生值 = `F44B0282BEA83557`**（不再是未知项）。
   - `signKey = c23.d()`（字段 `b`），写入源 = `k14.a.c(R.drawable.bg_contact_list)`。
   - `bg_contact_list` 是 **XML shape**（`res/drawable/bg_contact_list.xml`，484 字节，`<shape>/<corners>/<solid>`），`BitmapFactory.decodeResource` 返回 **null** → `k14.a.c` fallback 返回 `r01.e = "F44B0282BEA83557"`。
   - 因此 sign key 与字段加密 key **值相同**（fallback 机制，非"同一个 key"）。

2. **`K.b2s` 确认为 native**（`com.huachenjie.c.K`，dex 中 flags=0x109 = public static native）：
   - `String b2s(byte[], int)` —— 输入图片 RGBA 像素字节 + mode（env 9/11 → 1，否则 2）。
   - `void patch(...)` —— 同为 native。
   - 类共 4 个方法：`<clinit>`（Java）、`<init>`（Java）、`b2s`（native）、`patch`（native）。

### 仍未闭环（易盾函数级 VMP，静态不可还原）

3. **`K.b2s` 的 native 实现** —— 决定 `runImgRecord` 的图片派生值。
   - 实现在 `libNetHTProtect.so`（易盾壳）。全 SO 扫描（92 个 arm64 SO）**无任何** `com/huachenjie/c/K` / `b2s` / `DataComponent` / `RegisterNatives` 明文类名/方法名 → 证明易盾用**加密字符串 + 运行时解密 + RegisterNatives** 注册。
   - `JNI_OnLoad`（0x249cf8）反汇编确认为易盾壳入口：`FindClass` + 系列初始化/注册调用，类名字符串运行时解密。
   - 方法体被 VMP 化（函数级虚拟化，非原生 ARM 指令），静态还原需反编译 VMP 字节码解释器，属行业级难题；在「不发包、不动态 hook」约束下**不可行**。
   - **影响**：`runImgRecord = MD5(runRecordCode + "260826158.6.8" + K.b2s(hcj_bg_run_index 像素) + timestamp)` 的图片派生值无法离线精确还原。`hcj_bg_run_index` 是 PNG（70099 字节，非 XML），不走 fallback。

4. **`DataComponent` 大量 native 方法**（`L0`/`h1`/`z0`/`B1`/`C0`/`N0`/`O0`/`Q0`/`J0`/`d1`/`w`/`k1` 等约 80 个，dex 中全部 `public native`）：
   - 同属易盾 VMP（`libNetHTProtect.so`），native 方法体静态不可还原。
   - **但三个核心方法有 Java 层等价实现（检测逻辑已 100% 还原）**：
     - `L0(int cheatType) → List<InvalidReason>` ≙ **`hp8.e(int cheatType)`**（`com/zj/widget/hp8.java`，纯 Java）：生成 invalidType 25(GPS关闭)/58(步幅异常)/2(距离不足)/1(打卡点不足)/3(配速异常)/53(配速持续异常)。
     - `h1(boolean isValid, int cheatType) → Map` ≙ **`StopRunUtils.q`**（`com/huachenjie/running/utils/StopRunUtils.java`）：finish body 组装（runRecordCode/duration/distance/totalStep/stepInterval/paceInterval/targetPoints/alignType/pauseCount/pauseTimes/cheatList/status/invalidReasons/faceCheckRecordList/abnormalCodes）。
     - `z0() → Map<Integer,CheatResult>` ≙ **`sh1.b()`**（`com/zj/widget/sh1.java`）：cheatType 110 虚拟定位（`r22.a()` 反射 ServiceManager 检测 `service_mock_location`/`service_fl_ml`）。
   - 其余 native 方法（`B1` 配速判定、`C0/N0/O0/Q0` 打卡点、`J0` 围栏、`w` 配置、`k1` 开跑等）为运行期状态机，无纯静态等价实现，但**不影响离线伪造数据**（伪造数据不经过客户端状态机，直接构造上传 body）。

5. **strideMap 内部 key** —— 上传 stride 的 map 字段名。构造点在 native（`ApiDataComponent.b0` 的 `strideList` 由 native 层 DataComponent 传入），Java 反编译不可见，保持未知。上传外层格式（`strideList:[{map}] + strideInterval + runRecordCode`）已确认；模拟脚本当前用 `{"index","stride","time"}`（**推测值，未源码确认**）。

### 已明确的检测点（Java 层可见，补充）

- **cheatType 110 = 虚拟定位**（`r22.a()` 反射 `ServiceManager.getService("service_mock_location")` / `getService("service_fl_ml")`，命中即 `CheatResult(110, 文案, 0)`；文案来自 `R.string.running_cheat_type_virtual`）。
- **检测数据载体**（`RunningDataV2`）：`gpsAbnormalTimes`（GPS 异常计数）、`lastSegmentStepExceptionNum`（分段步数异常计数）、`lastSegmentStrideDistance`（分段步幅距离）、`segmentStrideExceptionNum`（允许异常数，`SchoolRule`）、`segmentStrideAvg`（平均步幅）。
- **步幅异常判定**（`hp8.java:280`）：`cheatLevel∈{3,4}` 且 `lastSegmentStepExceptionNum > segmentStrideExceptionNum` 且非白名单 → 异常（invalidType 58）。

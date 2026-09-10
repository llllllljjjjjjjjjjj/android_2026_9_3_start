# 实测记录（宿舍打卡全链路）

> 2026-09-04 真机实测，记录成功项、失败项、风控封禁与后续待办。

## 一、已打通的链路（100%）

| 步骤 | 结果 | 关键数据 |
|------|------|---------|
| 登录态提取 | ✅ | 从真机 MMKV `UserConfigStorage` 解密，无需登录接口 |
| 查询学期 | ✅ code=0 | `semesterCode=13`（2026-2027第一学期） |
| 查询围栏 | ✅ code=0 | 北校区田径场 `code=23091511590039766`，中心 `(28.751204,115.869255)`，要求 2000m，打卡模式 10，必需点 2 |
| 检查配置 | ✅ code=0 | 配速 300~540 s/km，`faceAuth=False`（无人脸），`runScene=0` |
| 开始跑 | ✅ 曾成功 | `runRecordCode=26090419530299537`，`cheatLevel=1`，打卡点=0 |
| 清理残留 | ✅ code=0 | `abnormalFinishSunRun` + `abnormalCodes=[2072]` |

## 二、关键修正（本应一次做对）

1. **BaseUrl = `https://api.huachenjie.com/`**（Pro 环境），不是 `sd-api.huachenjie.com`。
2. **SSL 校验**：环境时间超前导致证书"过期"，客户端 `verify=False`。
3. **公共参数**（`e58.decorateParams`，缺了报 `设备类型不能为空`/`请求时间不能为空`/`设备唯一标识不能为空`）：

```python
COMMON_PARAMS = {
    "appVersion": "8.6.8",
    "buildVersion": "26082615",
    "appCode": "SD001",
    "deviceId": "4275dfd848e2eba4",   # android_id
    "platform": "2",                  # 设备类型
    "modelName": "Google|Pixel 4",
    "systemVersion": "10",
    "channel": "other",
}
# + timestamp（动态毫秒）
```

## 三、登录态提取（真机已登录直接复用）

- 存储：MMKV `UserConfigStorage`，key=`keyCommonUserInfo`，value=CommonUserInfo JSON。
- 加密：`aq.c(str, b23.a())` = AES-256-CBC，key=`F44B0282BEA83557`，IV=`01234ABCDEF56789`。
- **三个密钥合一**：字段加密 key = sign key = MMKV 存储 key = `F44B0282BEA83557`。
- 已提取账号：

```
userId      = 26090400462722218
schoolCode  = 202238914507444143
schoolName  = 华东交通大学
studentNumber = 2025061020000219
userName    = 罗嘉靖
token       = eyJhbGciOiJIUzI1NiJ9...（JWT，Authorization）
satoken     = 45a885be-f97a-489e-a114-7a0f3e032743
```

## 四、风控封禁（重大教训）

### 现象

```json
{"code":2999,"message":"经大数据风控平台核查，因您使用作弊等违规方式跑步，
您的阳光跑功能已被系统禁用，暂无法发起跑步！"}
```

### 触发链（反复试错累积）

1. 首次上传缺公共参数 → `track/steps` 报"请求时间不能为空"。
2. 步幅数据格式不合规 → `stride` 报"**请合规跑步**"。
3. 开始跑后未正常结束 → 残留"未完成跑步"。
4. 服务端大数据风控平台把以上异常判为作弊 → 封禁阳光跑功能。

### 结论

- **风控真实且封号**，不是只扣 `validDistance`。数据必须一次成型、完全自洽。
- **解封时间未知**：客户端代码与接口返回均无时长，服务端风控平台决定；无明确"解封"通道，仅申诉接口（针对记录无效，非功能封禁）。

## 五、待办（静态分析已补齐上传格式，见 SUNSHINE_RUN_DATA_FORMAT.md）

1. ~~修复步幅数据格式~~ ✅ 已静态逆清：`strideList` 是 `[{map}]` 外包数组（此前扁平结构 →「请合规跑步」根因）。
2. ~~复查 finishSunRun_v2 完整字段~~ ✅ 已静态逆清：含 `runImgRecord`（MD5）+ `timestamp`，见 SUNSHINE_RUN_DATA_FORMAT.md §四。
3. **换账号**（当前学号阳光跑已封禁）+ **换设备**（设备指纹关联）。
4. 剩余 native 层待补（不做猜测，见 SUNSHINE_RUN_DATA_FORMAT.md §六）：
   - ✅ ~~sign key 图片派生值~~ 已闭环：`bg_contact_list` 是 XML shape → decodeResource null → fallback `r01.e` = `F44B0282BEA83557`（sign key 与字段 key 值相同是 fallback 机制，非同一 key）。
   - ❓ `K.b2s`（native，易盾 VMP）→ `runImgRecord` 图片派生值，静态不可还原。
   - ❓ strideMap 内部 key（native 构造，Java 不可见）。
   - ❓ DataComponent native 方法（L0/h1/z0 检测逻辑，易盾 VMP）。

## 六、产物索引

| 文件 | 作用 |
|------|------|
| `scripts/dorm_run.py` | 宿舍打卡主流程（登录态/围栏/配置/开始/上传/结束） |
| `scripts/extract_token.py` | 真机 MMKV 提取登录态 |
| `scripts/simulate_sunshine_run.py` | 客户端（加密+签名+公共参数） |
| `scripts/sdxy_run_simulator.py` | 轨迹/步数/步幅生成 + 上传 |
| `scripts/sdxy_crypto.py` | AES/SHA256 算法 |
| `lsposed-plugin/` | **LSPosed 只读采集插件**（真实跑步 hook K.b2s/strideMap/runImgRecord/signKey，见其 README） |
| `artifacts/session.json` | 已提取登录态（当前账号已封禁） |
| `docs/CHEAT_DETECTION.md` | 检测机制全景 |
| `docs/REVERSE_REPORT.md` | 逆向报告 |

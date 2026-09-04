# 阳光跑接口模拟实现说明

## 已还原（可直接用于模拟）

| 项 | 值 | 来源 |
|----|-----|------|
| 生产 BaseUrl | `https://api.huachenjie.com/`（Pro，env=9） | `libapp.so` 字符串 |
| 山东 BaseUrl | `https://sd-api.huachenjie.com/`（Sd，env=11） | `g33.a()` 环境映射 |
| 加密算法 | AES-256-CBC + PKCS7Padding，IV=`01234ABCDEF56789`，输出 Base64 | `com.zj.widget.cq` |
| 签名算法 | `AES(SHA256(json)旋转, sign_key)` → Base64 | `ParamsInterceptor.getSign` |
| SHA 旋转 | hex 末8位 + 中间 + 前8位 | `com.zj.widget.h58.c` |
| 字段加密 key | `F44B0282BEA83557`（env 9/11）；`huachenjie`（其他 env） | `r01.e` / `r01.f` |
| 敏感字段 | `phone, password, userName, schoolName, studentNumber` | `k14.d` 硬编码 |
| 请求头 | `app/api/v`（URL 前三段）、`pv`、`e`、`Authorization`、`satoken`、`sign` | `EncryptInterceptor.l` |

## sign key（已确定）

- `k14.c(ctx, pwdResId)` 用 `BitmapFactory.decodeResource` 解码密码图片。
- `pwdResId = 2131231070 = 0x7f08011e = R.drawable.bg_contact_list`（来自 `c80.java:90`）。
- `bg_contact_list` 是 **XML shape**（`res/drawable/bg_contact_list.xml`，484 字节，非位图）。
- `BitmapFactory.decodeResource` 对 XML drawable 返回 `null` → `k14.c` 走 fallback 返回 `r01.e`。
- 因此 **sign key == 字段 key == `F44B0282BEA83557`**。

> 交叉验证方式（可选，设备联网后）：触发任意业务请求后 attach 读 `c23.b`，应等于上述值。
> `frida_read_keys.py <PID>` 可读 `c23.a` / `c23.b`。

## 模拟客户端用法

```python
from simulate_sunshine_run import SdxyClient

c = SdxyClient(
    base_url="https://sd-api.huachenjie.com/",   # 或 api.huachenjie.com
    token="<登录 token>",
    satoken="<satoken>",
    sign_key="<动态获取的 c23.b>",
)

# 首页 -> 运动 -> 阳光跑
c.query_sun_run_abstract(semester_code, run_plan_code, sport_type)
c.check_sun_run_config(school_code, sub_school_code, target_distance, activity_code, run_plan_code, fence_code, sport_type)
c.start_sun_run(school_code, fence_code, activity_code, lat, lng, target_distance, use_credit_sword, run_plan_code, sport_type)
c.upload_run_record(record_body)
c.finish_sun_run(finish_body)
c.page_sun_run_record(page_size, page_num, semester_code, run_plan_code)
c.query_unfinish_run(sport_type)
```

## 阳光跑接口清单（`ISunshineApi` / `IRunApi`）

| 接口 | 方法 | 关键参数 |
|------|------|---------|
| `run-front/run/querySunRunAbstractInfoV2` | 阳光跑摘要 | semesterCode, runPlanCode, sportType |
| `run-front/run/checkSunRunConfig` | 检查配置 | schoolCode, subSchoolCode, targetDistance, activityCode, runPlanCode, fenceCode, sportType |
| `run-front/run/startSunRun_v2` | 开始阳光跑 | schoolCode, fenceCode, activityCode, lat, lng, targetDistance, useCreditSword, runPlanCode, sportType |
| `run-front/run/uploadRunRecord` | 上传跑步记录（sign header） | @Body JSON |
| `run-front/run/uploadPaceRecord` | 上传配速 | @Body JSON |
| `run-front/run/uploadPassPoint` | 上传途经点 | @Body JSON |
| `run-front/run/uploadStepsRecord` | 上传步数 | @Body JSON |
| `run-front/run/finishSunRun_v2` | 结束阳光跑 | @Body JSON |
| `run-front/run/queryUnFinishRun` | 未完成跑步 | @FieldMap |
| `run-front/run/resume` | 恢复跑步 | sportType, runRecordCode |
| `run-front/run/pageSunRunRecord` | 记录列表 | pageSize, pageNum, semesterCode, runPlanCode |
| `run-front/run/runRecordDetail` | 跑步详情 | runRecordCode, semesterCode |
| `run-front/rank/runProgress` | 阳光跑排名 | sex, scope, runPlanCode |
| `run-front/school/querySchoolFences` | 学校围栏 | schoolCode |

## 文件

- [sdxy_crypto.py](../scripts/sdxy_crypto.py) — 算法实现（可独立复用）
- [simulate_sunshine_run.py](../scripts/simulate_sunshine_run.py) — 阳光跑模拟客户端
- [frida_read_keys.py](../scripts/frida_read_keys.py) — 动态读密钥
- [REVERSE_REPORT.md](REVERSE_REPORT.md) — 完整逆向报告

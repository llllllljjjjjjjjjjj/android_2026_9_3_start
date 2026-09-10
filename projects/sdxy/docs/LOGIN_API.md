# sdxy（闪动校园）登录接口逆向分析

> 目标 APK：`projects/sdxy/apk/sdxy.apk`（包名 `com.huachenjie.shandong_school`，v8.6.8 / code 26082615）
> 反编译源：`projects/sdxy/decompiled_biz/all/sources/`（12 业务 dex 合并，方法体完整）
> 本文件聚焦 **登录**：登录形态矩阵、请求通用传输层（拦截器链）、各登录接口定义、字段来源调用链、响应会话注入、错误码表、离线复现状态。
> 加密/签名算法字节级还原与密钥推导 → 见 `REVERSE_REPORT.md` §3-§4、`CORE_CLASSES_ANALYSIS.md`；请求密钥实现 → `scripts/sdxy_crypto.py`。

---

## 1. 登录形态总览

App 登录不是单接口，而是「账号预检 → 分流 → 凭证换取 token」的流程族。同一传输层（§2）套在不同接口上。

```
WelcomeLoginActivity（手机号/校友ID 输入）
   │  RequestModel.l(loginName) ── POST run-front/auth/loginCheck ── LoginCheckData
   │        {phone, passwordType, loginType}
   ▼ 按 loginType 分流
   ├─ PASSWORD(1) ──► PasswordActivity  →  POST run-front/auth/loginPassword {loginName, password, captchaPoint?}
   ├─ SMS_CODE(2)  ──► VerifyCodeActivity → ① POST run-front/account/getAuthCode {phone, sendType, ...} → AuthCodeData{ticket}
   │                                        ② POST run-front/account/login_v3 {phone, authCode, ticket}
   └─ 三方入口（微信/QQ/学校）──► thirdLogin_v2 / sso/phone/bind / sso/phone/bind/verify（见 §4.3/§4.5）
                                                      │
                                                      ▼
                           LoginResultData {userId, token, satoken, userType, currentTip, alertTip}
                           → token→Authorization 头、satoken→satoken 头（mo1 单例注入，见 §5）
```

| 接口（path 前缀均为 `run-front/`） | Retrofit 锚点 | header `e` | 说明 |
|---|---|---|---|
| `auth/loginCheck` | LoginApi.n | 1 | 账号预检（1605=不存在） |
| `account/getAuthCode` | LoginApi.i（FieldMap 版，实际使用）| 1 | 发短信/语音验证码 → `AuthCodeData{ticket}` |
| `account/login_v3` | LoginApi.p | 1 | 验证码登录（None 三方场景） |
| `auth/loginPassword` | LoginApi.e | 1 | 密码登录 |
| `account/thirdLogin_v2` | LoginApi.s | — | 三方登录（JSON Body） |
| `account/sso/phone/bind` | LoginApi.a | — | 学校认证绑手机（发码） |
| `account/sso/phone/bind/verify` | LoginApi.o | — | 学校认证绑手机核验（完成登录） |
| `auth/sso/casCallback` | LoginApi.b | — | CAS ticket 换 SchoolAuthBean |
| `login/setPassword_v2` / `login/resetPasswordOut` | LoginApi.c / j | 1 | 首次设密 / 忘记密码 |
| `login/getPasswordSetCode` | LoginApi.t | 1 | 设密验证码（`PasswordVerifyCodeData`） |
| `account/sendRemainTimes` | LoginApi.l | 1 | 发码前查剩余次数 `RemainTimesData` |
| `account/oneClick/login` | LoginApi.h | — | 个推一键登录（geTuiToken/gyuid） |
| `auth/bindVisitor` | LoginApi.m | 1 | 游客绑定（JSON Body） |

> 判断依据：`com.huachenjie.login.api.LoginApi.java`（Retrofit 接口）+ `RequestModel.java`（Repository 层封装，标注了每个方法实际拼的参数 map）。

---

## 2. 通用传输层（登录与全部业务请求共用的骨架）

### 2.1 OkHttp 拦截器装配（初始化处 `com.zj.widget.k14.d` → `wh7.h(builder)`）

`wh7.a` Builder 的 `B(Interceptor)` = `addInterceptor`（`wh7.java`）。k14.d 中添加顺序：

```java
wh7.h(new wh7.a().r(Environment.a)          // baseUrl
        .s(15000).F(15000)                  // connect/read timeout(ms)
        .u(ctx).w(hcj_debug)
        .B(new bm5())                       // mock 拦截器，开关 am5 关闭时直通（无影响）
        .B(new g19())                       // 响应 code 1005/1503/1504 → 登出/踢出（token 失效）
        .t(jv3.b())                         // fastjson Converter
        .B(new EncryptInterceptor(...))     // ① 字段加解密（FormBody→JSON）
        .B(e58Var)                          // ② ParamsInterceptor 子类：公共参数 + sign
        .B(d14.a())                         // HttpLoggingInterceptor(NONE)
        .E(false) ...);                     // 不做自定义 SSL 校验（默认信任链）
RetrofitClient.INSTANCE.a().c(Environment.a, wh7.e().f());
```

**有效链 = EncryptInterceptor → e58（顺序即执行顺序，add 序）**。bm5/d14 直通，g19 只做响应兜底跳登录。

### 2.2 一次登录 POST 在链上的逐级变换（以 `loginPassword` 为例）

**阶段 0 — Retrofit 原始请求**（`FormUrlEncoded @POST run-front/auth/loginPassword`，注解 `@Headers({"e:1"})`）：

```
POST /run-front/auth/loginPassword HTTP/1.1
Content-Type: application/x-www-form-urlencoded
e: 1

loginName=<明文账号>&password=<明文密码>            ← FormBody
```

**阶段 1 — EncryptInterceptor（`huachenjie/sdk/http/security/core/EncryptInterceptor.java`）**：
- `f()`：URL path 前 3 段 → header `app=run-front / api=auth / v=loginPassword`。
- `l()`：`headers` 增加 `app/api/v`，`pv` 缺省补 `2`，`e` 保留原值（登录接口是 `1` = 启用字段加密；`0`/缺失/GET → 跳过本阶段直接 JSON 化）。
- `g(request)` = GET || e 空/`0` || `c23.f()`(开关) → true 时不加密。登录接口 e:1 → 走加密分支。
- `i()`：FormBody 整体解析为 key-value。
- **`d(json)`：仅对敏感字段名单 `c23.c()` 中的键值做 `cq.c(value, c23.b())`（AES-256-CBC+Base64）**，其余原样。名单硬编码于 `k14.d`：

  ```java
  ["phone", "password", "userName", "schoolName", "studentNumber"]
  ```

  → 登录请求中 **`password` 值在链上被 AES 加密**（loginName/captchaPoint 不动）。
- `m()`：`POST application/json` 重建 body，但 **headers 保持原集合**（Content-Type 仍是 form-urlencoded，body 已是 JSON 文本——服务端按 body 解析，模拟端实测兼容）。

**阶段 2 — e58（`com.zj.widget.e58`，extends `huachenjie...ParamsInterceptor`）**：
- 读到的是 JSON body（非 FormBody/非 multipart）→ `ParamsInterceptor.h()`：
  `JSON.parse(body)` → **`decorateParams(map)`（e58.m）**：

  ```java
  // 键缺失才补（业务已带则保留）；timestamp 缺省补 (now + mo1.f12469a)
  timestamp  = System.currentTimeMillis() + mo1.f12469a      // f12469a = 服务器时间偏移，SyncTimeIntentService 同步 z70.B() 写入
  appVersion = mo1.c = "8.6.8"        buildVersion = mo1.d = "26082615"
  appCode    = mo1.i = "SD001"        deviceId   = mo1.e = jl2.b(ctx)
  platform   = mo1.f = "2"            modelName  = mo1.g = Build.MANUFACTURER|"|"|MODEL
  systemVersion = mo1.h               channel    = mo1.k = "other"
  ```

  `l()`：已存在键不覆盖 → 业务参数优先。
- 序列化回 JSON（`on4.h(map)`，fastjson）→ `c()`：**`sign = getSign(map)`**：

  ```java
  sign = cq.c( h58.c( JSON.toJSONString(map) ), c23.d() )
       = AES-256-CBC( SHA256( JSON ) 旋转, signKey ) → Base64
  ```

  写入 header `sign`（仅当请求原本无 sign header）。**登录接口同样会带 sign**（客户端侧必然计算；服务端是否对 e:1 登录接口强制验签未实证，见 §6）。
- `wrapPostRequest()`：UA 换成 `mo1.j` = `"ShanDong/8.6.8 (<brand>;Android <RELEASE>)"`；`a()` 在已登录态注入 `Authorization = mo1.f12470a(token)`、`satoken = mo1.b`。

### 2.3 线上请求实态（静态推演，模拟端已按此跑通 sign code=0）

```
POST https://api.huachenjie.com/run-front/auth/loginPassword HTTP/1.1
Content-Type: application/x-www-form-urlencoded      ← 保留原类型（body 实为 JSON 文本）
e: 1
pv: 2
app: run-front
api: auth
v: loginPassword
User-Agent: ShanDong/8.6.8 (Google;Android 10)
sign: <AES(SHA256(JSON)→旋转, F44B0282BEA83557) Base64>

{"loginName":"<明文>","password":"<AES密文>","timestamp":"1788...","appVersion":"8.6.8",
 "buildVersion":"26082615","appCode":"SD001","deviceId":"4275dfd848e2eba4",
 "platform":"2","modelName":"Google|Pixel 4","systemVersion":"10","channel":"other"}
```

### 2.4 算法速查（字节级实现见 `scripts/sdxy_crypto.py`，已自检）

| 项 | 值 |
|---|---|
| 字段加密 / sign AES | `AES-256-CBC / PKCS7(PKCS5) / IV="01234ABCDEF56789"`，key = UTF-8 截断/右补零 32B |
| 字段 key `c23.b()` / sign key `c23.d()` | **均为 `F44B0282BEA83557`**（env Pro=9 / Sd=11 时取 `r01.e`；其他 env 为 `huachenjie`；sign key 是 XML shape 资源 fallback 的结果，两 key 值相同≠同一 key） |
| hash | `SHA-256` hex → 字符串旋转：`hex[-8:] + hex[8:-8] + hex[:8]` |
| Base64 | Android `Base64.NO_WRAP` |
| BaseUrl | Pro(env 9)=`https://api.huachenjie.com/`；Sd(env 11)=`https://sd-api.huachenjie.com/`（FIELD_TEST 实测走 Pro） |
| 响应信封 | `BaseEntity {code, msg, data}`；`data` 内敏感字段由 EncryptInterceptor 响应侧解密（`cq.a`）后到 VM |

---

## 3. 密码登录（主形态）

### 3.1 调用链

```
WelcomeLoginActivity: account 输入 → WelcomeLoginVM.n() [checkAccount] 
  → WelcomeLoginVM$checkAccount$2 → RequestModel.l(loginName) 
  → RequestModel$loginCheck$2 → LoginApi.n: @FormUrlEncoded @Headers({"e:1"})
    POST run-front/auth/loginCheck  Field{loginName}
  → LoginCheckData{phone, passwordType, loginType}  （1605 校友ID不存在）

loginType==PASSWORD(1) → PasswordActivity（Intent extra "loginPhone" = 预检返回 phone）
  → PasswordActivity 按钮 → PasswordVM.n(loginName=loginPhone, captchaPoint) 
  → PasswordVM$loginPassword$2 → RequestModel.m(loginName, password, captchaPoint)
  → RequestModel$loginPassword$2 → LoginApi.e: @Headers({"e:1"})
    POST run-front/auth/loginPassword  Field{loginName, password, captchaPoint?}
  → LoginResultData
```

### 3.2 参数

| 字段 | 值 | 链上处理 |
|---|---|---|
| `loginName` | 手机号（校友预检返回的 phone；welcome 页也接受校友ID 输入） | 明文 |
| `password` | 用户输入原密码（**客户端不做摘要**，明文入 FormBody） | **EncryptInterceptor 字段级 AES 加密** |
| `captchaPoint` | 图形验证码点位串（服务端 1600 要求时返回后二次提交） | 明文，可空 |

`password` 不经 MD5/SHA 直接参与字段加密：`encrypt_field(pw, "F44B0282BEA83557")`（`sdxy_crypto.encrypt_field` 一致）。

---

## 4. 验证码 / 三方 / 附属登录

### 4.1 发验证码 getAuthCode（前置两次检查）

调用链：`VerifyCodeActivity → SendVerifyCodeUtil.e/g/i → sendAuthCode$2`

```
① 次数预检   RequestModel.d(phone) → LoginApi.l @Headers({"e:1"})
            POST run-front/account/sendRemainTimes Field{phone}
            → RemainTimesData{smsLoginRemainTimes, callLoginRemainTimes}
            （sms==0 提示改语音 / call==0 达上限；code 1514/1526 归零）

② 发码      按 loginThirdType 分支（None=0 普通登录）：
   None:   RequestModel.r(phone, sendType, captchaPoint?)
           map{phone, sendType} → LoginApi.i @FieldMap @Headers({"e:1"})
   School: RequestModel.s(...)  → bindPhoneAuthCode
   其他三方: RequestModel.t(phone, sendType, thirdType, captchaPoint?)
           map{phone, sendType, "type":"3", thirdType, captchaPoint?}
           → LoginApi.i @FieldMap e:1
           POST run-front/account/getAuthCode
           → AuthCodeData{ticket}
```

- `sendType`：`VerifyCodeType` SMS=1 / VOICE=2（`VerifyCodeType.java`）
- `type`：普通登录不发；三方场景固定 `"3"`（`RequestModel.t`）
- `captchaPoint`：服务端要求图形验证码（code 1600）时带
- 客户端 60s 节流（`SendVerifyCodeUtil.e`），响应 ticket 缓存于 `VerifyCodeParams.lastSendTicket` → 登录时提交

### 4.2 验证码登录 login_v3（None 三方 = 普通手机号登录）

```
VerifyCodeActivity → VerifyCodeVM.u(verifyCode) → VerifyCodeVM$login$1
  → RequestModel.k(phone, authCode, ticket)
  → RequestModel$loginByVerifyCode$2 → LoginApi.p @Headers({"e:1"})
    POST run-front/account/login_v3  Field{phone, authCode, ticket}
  → LoginResultData
```

三个字段均敏感名单内 `phone` → 线上 `phone` 被 AES 加密（authCode/ticket 明文）。`ticket` 为发码响应唯一字段（`AuthCodeData`），缺失时 VM 直接拒绝（`login_input_ticket_empty`）。

### 4.3 三方登录 thirdLogin_v2（微信/QQ）

```
BaseLoginVM.m(thirdType, thirdKey) → BaseLoginVM$thirdLogin$2 → RequestModel.v(...)
  map{thirdType: <int>, code: <三方授权码/凭据>, phone:"", authCode:"", ticket:""}
  JSON.toJSONString(map) → RequestBody(application/json) → LoginApi.s
    POST run-front/account/thirdLogin_v2
  → LoginResultData（error 6500 = 三方账号未绑定 → 跳绑定页，绑定完成回填 phone/authCode/ticket 再登）
```

- `thirdType`：`LoginThirdType` None=0 / WeiXin=1 / QQ=2 / School=3
- `code` 的 key 常量 = `VerifyCodeActivity.y`
- 登录成功前的手机号绑定同样走此接口（map 带 phone/authCode/ticket 与三方标识）

### 4.4 一键登录 oneClick/login（个推闪验）

```
RequestModel.n(geTuiToken, gyuid) → LoginApi.h
  POST run-front/account/oneClick/login Field{geTuiToken, gyuid}
```

### 4.5 学校（校友）认证登录族（v8.6.8 的「校友」通道）

| 步骤 | 接口 | 关键字段 |
|---|---|---|
| 配置列表 | `sso/school/getConfigList`（LoginApi.g） | pageNum/pageSize |
| 绑手机发码 | `account/sso/phone/bind`（LoginApi.a） | schoolCode/number/phone/bindKey |
| 完成绑定即登录 | `account/sso/phone/bind/verify`（LoginApi.o） | schoolCode/number/phone/code/bindKey/ticket |
| CAS 回调 | `auth/sso/casCallback`（LoginApi.b） | schoolCode/ticket/type |

对应 VM 分支（`VerifyCodeVM$login$1`）：`loginThirdType==School(3)` 时字段拼接 `{schoolCode, studentNumber, phone, code, bindKey, ticket}`（`RequestModel.j`）。

### 4.6 游客 / 设密 / 重置

- `auth/bindVisitor`（LoginApi.m）：JSON Body `VisitorRequestBean` → `BindVisitorBean`
- `login/setPassword_v2`（LoginApi.c）：`{ticket,password,authCode,phone}` e:1
- `login/resetPasswordOut`（LoginApi.j）：`{ticket,password,authCode,phone}` e:1
- `login/getPasswordSetCode`（LoginApi.t）：`{phone,captchaPoint?}` e:1 → `PasswordVerifyCodeData`

---

## 5. 响应与会话注入

### 5.1 LoginResultData 字段（`login/bean/LoginResultData.java`）

```kotlin
data class LoginResultData(
  userId: String,     // 用户 ID（session.json 实测 19 位数字）
  token: String,      // JWT HS256（Authorization 值，无 Bearer 前缀）
  satoken: String,    // UUID 会话（独立 header satoken）
  userType: Int,      // 2=正式学生；新用户首登走补资料
  currentTip: Boolean?,
  alertTip: AlertTip?,
)
```

token 是 JWT：`header={"alg":"HS256"}`，`payload={uid, exp, phone, iat}`（解密 artifacts/session.json 实测）。

### 5.2 注入点（登录成功后一次写入，全 App 生效）

`LoginUtil.b(context, vm, result)`（`login/util/LoginUtil.java`）：

```java
wh7.e().g().n().f12470a = result.getToken();    // → e58/ParamsInterceptor.a(): header "Authorization"
wh7.e().g().n().b      = result.getSatoken();   // → header "satoken"
na9.q(CommonUserInfo(userId, userType, token, satoken));  // 持久化（MMKV "CommonUserInfo"）
```

之后每次请求由 `ParamsInterceptor.a()` 经 `mo1` 注入这两个头（已存在同名头则不覆盖，`filterHeader`）。持久化侧：`na9.c().getToken()` 冷启动回填（`k14.d` 中 `mo1.c(z70.B(), na9.c().getToken(), na9.c().getSatoken(), jl2.b(ctx))`）。服务端踢人（code 1005/1503/1504）由 g19 拦截器统一登出。

### 5.3 响应信封

`data` 内敏感字段（名单同请求）由 EncryptInterceptor 响应侧 `c()` 用 `cq.a(…, c23.b())` 解密后交 VM——即业务代码读到的 phone 是明文。**HTTP 200 ≠ code=0**：业务成功以 `BaseEntity.code==0` 为准（ResultException 语义见 §7 表）。

---

## 6. 复现状态与止损点（重要）

| 事项 | 状态 | 说明 |
|---|---|---|
| 传输层（字段加密/公共参数/sign） | ✅ 实测 code=0 | `scripts/sdxy_run_simulator.py` SdxyClient + 阳光跑全链路；`FIELD_TEST_LOG.md` |
| 登录后业务请求（token 注入） | ✅ 实测 | `test_apis.py` 用 session.json 登录态查只读接口 |
| **1600 滑块验证码全自动** | ✅ **已闭环** | `scripts/login_full.py` 滑块 solver；`x = 模板中心C − 13.5`、key=`Ukp3hmSe7BmMcgbE`、y=15，`check` result:true |
| **密码登录（PC 全自动）** | ✅ **实测登录成功** | `login_full.py`：滑块→captchaPoint→`loginPassword` → `code=0`，userId=26090400390821949，token/satoken 已入 `artifacts/session.json` |
| 验证码登录（login_v3） | 🟡 结构/加密就绪 | `login_full.py` 已含 `getAuthCode`（带 captchaPoint）路径；**仍需要真实短信验证码**才能完成 login_v3（getAuthCode 发码已过 1600） |
| 三方登录 | ⛔ 需授权 | 微信/QQ OAuth 授权码不可离线伪造 |

**待实证项（已闭合）**：① 服务端对 `e:1` 登录接口**不强制校验 sign**（模拟端不带 sign 也到业务层 + 登录成功）；② 真实 Content-Type（模拟端用 json 发送，服务端按 body 解析，兼容）；③ `timestamp` 偏移由 `SyncTimeIntentService` 同步 `z70.B()`；④ 滑块坐标映射已由真机成功样本定标。

**模拟器用法**（已有登录态跑业务）：

```python
from scripts.simulate_sunshine_run import SdxyClient
c = SdxyClient(base_url="https://api.huachenjie.com/",
               token=sess["token"], satoken=sess["satoken"],
               sign_key="F44B0282BEA83557")
```

### 6.1 在线首测记录（账号 13407006275）

| 接口 | 请求 | 结果 |
|---|---|---|
| `auth/loginCheck` | e:1 + 公共参数 + **sign** | ✅ **code=0**，且 `data.phone` 为服务端 AES 密文（`decrypt_field(..., F44B0282BEA83557)` 还原 `13407006275`）——**证明 sign 算法与服务端字节级一致 + 敏感字段加密名单两端一致** |
| `account/sendRemainTimes` | e:1 + 公共参数 + sign | ✅ code=0，`{smsLoginRemainTimes:4, callLoginRemainTimes:2}` |
| `auth/loginPassword` | e:1 + 字段加密（password AESE）+ 公共参数（无 sign） | ⚠️ **code=1600**「未执行账户验证」→ 需图形验证码 |
| `account/getAuthCode` | e:1 + 公共参数 + sign | ⚠️ **code=1600** → 发短信同样过滑块 |

### 6.2 1600 图形滑块验证码——已全自动闭环（2026 实测）

**服务端前置门槛是 code=1600 自研滑块验证码**（H5 `blockPuzzle`），协议与坐标口径均已逆向并经真机成功样本标定，PC 端可**完全自动**通过：

```
① POST /run-front/captcha/get  {captchaType:"blockPuzzle"} → {originalImageUrl, jigsawImageUrl, token}
② 图像定位缺口：cv2.matchTemplate(原始图, 拼块) → 取最佳匹配中心 x=C
      x = C - 13.5                    （310 设计体系；真机标定：C=170.5 → x=157.0 通过）
③ pointJson = AES-128-ECB( JSON({x, y:15}), key=Ukp3hmSe7BmMcgbE ) → Base64
④ POST /run-front/captcha/check {captchaType, pointJson, token} → {result:true}
⑤ captchaPoint = pointJson → 带 `captchaPoint` 提交 loginPassword / getAuthCode
```

**关键确认（真机 hook 捕获成功样本标定）**
- 加密 key = **`Ukp3hmSe7BmMcgbE`**（App `JavascriptApi.getSecretKey` 返回，AES-128-ECB + PKCS7 + Base64；前端 fallback 默认值是另一常量，无效）
- **y 恒 = 15**（服务端只判 x；y=15 固定），pointJson 结构 `{"x":E,"y":15}`
- **x = 槽模板匹配中心 − 13.5**（成功样本：队模板中心 155.50 ↔ 服务端接受 x=141.9345，差 13.565≈13.5，即前端 `E=(e+d)*310/imgWidth+10` 的折算）
- 服务端对 pointJson 也接受**明文 JSON**（`empty` 才报 code=201，无法解析/错误值统一按 `result:false`）
- 服务端对同 token 多次 `check` 失败不封号（已大量扫描验证），但建议低频率避免风控

**标定方法（沉淀）**：真机 Hook `JavascriptApi.Y`（`checkResult`）捕获成功 `pointJson` + Hook `RealInterceptorChain` 捕获同次 `getCaptcha` 图片 URL，把「图像槽位模板中心 C」与「服务端接受的 x」配对，得 `x = C − 13.5`。

**PC 全自动登录实现**：`scripts/login_full.py`（滑块 solver + 密码登录，实测**code=0 登录成功**，userId=26090400390821949，token/satoken 已写入 `artifacts/session.json`）。滑块 solver 复用 `scripts/captcha_solver.py`。

> 待实证项现已全部闭合：sign 是否强制（登录接口不带 sign 也到业务层）、Content-Type（模拟端用 json 兼容）、timestamp 偏移由 `SyncTimeIntentService` 同步、滑块坐标映射已定标。

---

## 7. 错误码语义（登录域，采集自 VM/ResultException 分支）

| code | 语义 | 客户端行为 |
|---|---|---|
| 0 | 成功 | — |
| 1600 | 需图形验证码 | PasswordVM/发码流程弹 CaptchaDialog → 带 `captchaPoint` 重试 |
| 1605 | 校友ID 不存在 | toast「校友ID不存在，换手机号试试」 |
| 10101 | 该账号需切验证码登录 | PasswordVM `needCodeLogin=true` → 跳验证码页 |
| 1514 | 短信登录次数耗尽 | 置 `smsLoginRemainTimes=0`；改语音码或明示 |
| 1526 | 语音登录次数耗尽 | 置 `callLoginRemainTimes=0` |
| 1530/1531/1534/1535 | 风控/频控类 | 对话框提示服务端 message |
| 1532/1533 | 设备登录过多 | 专属标题「登录设备过多」 |
| 1536/1537 | 账号登录设备过多 | 专属标题 |
| 6500 | 三方账号未绑定 | BaseLoginVM `thirdLoginBindData` → 跳绑定手机号流程 |
| 1005/1503/1504 | token 失效/被踢 | g19 拦截器 → ARouter `/compat/logout` |

> 风控记录：发送验证码链路存在多级次数限制（sendRemainTimes 预检 + 服务端 1514/1526 + 客户端 60s 节流）；密码错误频控与图形验证码（1600）绑定。实测定量数据见 `docs/risk-observations.md`（如有）。1532/1533 与 1536/1537 的精确触发阈值需真机实测补录。

---

## 8. 关键源码索引

| 内容 | 文件 |
|---|---|
| Retrofit 接口定义 | `com/huachenjie/login/api/LoginApi.java` |
| Repository 层参数拼装 | `com/huachenjie/login/api/RequestModel.java`（+ `RequestModel$*$2` lambda） |
| 密码登录页 VM | `login/page/password/PasswordVM.java`、`PasswordVM$loginPassword$2.java` |
| 验证码登录页 VM | `login/page/verify_code/VerifyCodeVM.java`、`VerifyCodeVM$login$1.java` |
| 欢迎页预检 | `login/page/welcome/WelcomeLoginVM.java`、`WelcomeLoginVM$checkAccount$2.java` |
| 发码工具 | `login/util/SendVerifyCodeUtil.java`（+ `checkVerifyTimes$2` / `sendAuthCode$2`） |
| 三方入口 | `login/page/base/BaseLoginVM.java`、`BaseLoginVM$thirdLogin$2.java` |
| 会话注入 | `login/util/LoginUtil.java`、`com/zj/widget/mo1.java`、`na9`、`wh7` |
| 网络初始化（key/名单/拦截器） | `com/zj/widget/k14.java`、`wh7.java`、`com/zj/widget/e58.java`（decorateParams 子类） |
| 字段加解密拦截器 | `huachenjie/sdk/http/security/core/EncryptInterceptor.java` |
| 签名拦截器 | `huachenjie/sdk/http/interceptor/ParamsInterceptor.java` |
| 算法实现 | `com/zj/widget/{cq,cl0,h58,c23}.java`、`scripts/sdxy_crypto.py` |
| 环境/域名 | `com/zj/widget/g33.java`、`com/huachenjie/common/constants/Environment.java` |
| 枚举 | `login/enums/{LoginType,LoginThirdType,VerifyCodeType,VerifyLimitType}.java` |
| 响应 bean | `login/bean/{LoginResultData,AuthCodeData,LoginCheckData,RemainTimesData,VerifyCodeParams}.java` |

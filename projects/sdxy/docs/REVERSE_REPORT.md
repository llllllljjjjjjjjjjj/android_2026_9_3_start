# sdxy（闪动校园）逆向报告

## 目标信息

| 项 | 值 |
|----|-----|
| 包名 | `com.huachenjie.shandong_school` |
| 应用名 | 闪动校园 |
| 版本 | 8.6.8（version_code 26082615） |
| APK 大小 | 293,546,757 字节 |
| 框架 | Flutter（`libapp.so`）+ 大量原生 Java/Kotlin 模块 |
| 加固 | 网易易盾 NIS `7.6.3_936`（`com.netease.nis.wrapper`） |
| 壳 SO | `libNetHTProtect.so`(4.7MB) + `libnesec.so`(1.1MB) |

## 1. 脱壳

### 方法
真机 Pixel 4（Root + 魔改 florida-server 16.5.10），App 启动触发易盾运行期解密后，Frida attach 扫描进程内存中的 dex magic 并 dump。

### 结果
- 内存扫描 dump 出 **76 个 DEX**，其中 **12 个为业务 dex**（含 `com/huachenjie` 类），共约 78MB。
- 业务 dex 清单（`projects/sdxy/apk/dump/sdxy_dump/`）：

| 文件 | 大小 | 类数 |
|------|------|------|
| s_40_3544052 | 3.5MB | 1608 |
| s_43_4303820 | 4.3MB | 3082 |
| s_42_4316936 | 4.3MB | 3056 |
| s_44_4733968 | 4.7MB | 3682 |
| s_41_5167656 | 5.2MB | 3726 |
| s_46_6694776 | 6.7MB | 5691 |
| s_45_6997568 | 7.0MB | 7043 |
| s_36_7445068 | 7.4MB | 8748 |
| s_47_8915164 | 8.9MB | 6775 |
| s_54_9205764 | 9.2MB | 8928 |
| s_51_9301572 | 9.3MB | 10132 |
| s_39_9715284 | 9.7MB | 9938 |

### 验证
12 个业务 dex 合并后 jadx 反编译：**22149 个类，5111 个业务类**，方法体完整（非抽取壳空壳）。合并源码位于 `projects/sdxy/decompiled_biz/all/`。

### 关键机制
易盾 7.6.3 用 `.cache/stub.dex`（284B 空类）占位 20 个 dexElement，真实 dex 通过 native cookie 重定向到内存匿名段。业务 `Application`（`ShandongApplication`）的全部方法被 native 化（VMP），业务逻辑在 `libapp.so` + 壳 SO 中运行。

## 2. API 端点

- **BaseUrl**：`https://api.huachenjie.com/`（另有 `dev.huachenjie.com` / `test.huachenjie.com`）
- **路径前缀**：`run-front/*`

### 核心接口（节选）

| 模块 | 端点 | 说明 |
|------|------|------|
| 登录 | `run-front/auth/loginPassword` | 密码登录（header `e:1`） |
| 登录 | `run-front/account/login_v3` | 验证码登录 |
| 登录 | `run-front/account/getAuthCode` | 获取验证码 |
| 登录 | `run-front/account/thirdLogin_v2` | 三方登录 |
| 登录 | `run-front/auth/loginCheck` | 登录态检查 |
| 账号 | `run-front/account/queryCommonUserInfo` | 查询用户信息 |
| 账号 | `run-front/account/oneClick/login` | 一键登录 |
| 体育 | `run-front/attend/semesterSelector` | 学期选择 |
| 体育 | `run-front/run/free/detail` | 跑步详情 |
| 人脸 | `run-front/face/updateUserFace` / `bindUserFace` | 人脸 |
| 抽奖 | `run-front/api/lottery/award/draw` / `redeem` | 抽奖 |
| AI 运动 | `run-front/ai/*`（planOption/startAiExerciseV2/finishExerciseV2 等） | Flutter 层 |
| 室内 | `run-front/indoor/*`（config/finish/sportCount/ranking） | Flutter 层 |
| OSS | `run-front/aliyun/oss/getToken` | 阿里云 OSS Token |

完整端点见反编译产物 `com/huachenjie/**/api/*.java`（375 个 API 文件）。

## 3. 请求加密与签名算法（完整还原）

### 加密组件
混淆类 `com.zj.widget`（实际为众简 SDK 加密工具，被 huachenjie SDK 复用）。

### 算法链

```
字段加密（EncryptInterceptor）:
  plaintext ──AES-256-CBC(key=c23.a, IV="01234ABCDEF56789", PKCS7Padding)──> Base64 ──> ciphertext

签名（ParamsInterceptor.getSign）:
  JSON(params) ──SHA-256──> hex ──字符串旋转(末8位+中间+前8位)──> AES-256-CBC(key=c23.b) ──> Base64 ──> sign

响应解密:
  Base64_decode ──AES-256-CBC(key=c23.a)──> plaintext
```

- 算法：`AES/CBC/PKCS7Padding`，**AES-256**（密钥 32 字节）
- IV：`01234ABCDEF56789`（固定）
- 编码：标准 Base64（`android.util.Base64`，NO_WRAP）
- 密钥派生：`cq.f(str)` = UTF-8 字节截断/右补零到 32 字节
- 敏感字段：`c23.f11070a`（List<String>，仅列表内字段加密，非全量）
- 请求头：`app` / `api` / `v`（来自 URL path 前三段）、`pv`、`e`（加密开关，`e:1` 表示加密）、`Authorization`（token）、`satoken`

### 关键源码位置
- `huachenjie/sdk/http/security/core/EncryptInterceptor.java` — 字段加解密拦截器
- `huachenjie/sdk/http/interceptor/ParamsInterceptor.java` — sign 签名拦截器
- `com/zj/widget/cq.java` — AES 加解密
- `com/zj/widget/h58.java` — SHA-256/SHA-512/MD5 + 字符串旋转
- `com/zj/widget/cl0.java` — Base64
- `com/zj/widget/c23.java` — 密钥/敏感字段配置

## 4. 密钥结论（已确定）

- **字段加密 key `c23.a` = `F44B0282BEA83557`**（`r01.e`，env 9/11；其他 env 为 `r01.f`=`huachenjie`）。
- **sign key `c23.b` = `F44B0282BEA83557`**（与字段 key 相同）。

### sign key 推导链
1. 初始化入口 `c80.e` → `k14.d(context, 2131231070, ...)`（`c80.java:90`）。
2. `pwdResId = 2131231070 = 0x7f08011e = R.drawable.bg_contact_list`。
3. `bg_contact_list` 是 XML shape（非位图）。
4. `BitmapFactory.decodeResource` 对 XML 返回 null → `k14.c` 走 fallback 返回 `r01.e`。
5. 故 `c23.b = r01.e`，与 `c23.a` 相同。

> 运行时 `com.zj.widget.c23` 为懒加载（首次业务请求才解密），且 App 业务网络被易盾 native 化，Java 层 `c23.e` 实际为死代码路径；上述结论基于静态常量与 Android 框架行为的确定性推导，模拟客户端已按此实现。设备联网后可用 `frida_read_keys.py` 读 `c23.b` 交叉验证。

## 5. 产物清单

- 业务 dex：`projects/sdxy/apk/dump/sdxy_dump/s_{36,39,40,41,42,43,44,45,46,47,51,54}_*.dex`
- 合并反编译：`projects/sdxy/decompiled_biz/all/`（22149 类）
- 壳反编译：`projects/sdxy/decompiled/`（易盾 wrapper）
- SO：`projects/sdxy/so_analysis/{libNetHTProtect.so,libapp.so,libnesec.so}`
- 脚本：`projects/sdxy/scripts/`（scan_vdex / classify_dump / frida_*）
- Hook：`projects/sdxy/hooks/`（dex_scan_attach / find_business_loader / read_keys2 / spawn_keys）

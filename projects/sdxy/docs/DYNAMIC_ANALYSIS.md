# 动态分析记录（2026-09-07 真机实测）

> 真机 Pixel 4（9C181EC3BF7E0D），florida frida-server + LSPosed + Zygisk 就绪。
> 本文件记录动态 hook / 接口实测的确定性结论，与静态分析交叉验证。

## 一、类加载状态（决定性发现）

Frida attach 主进程（pid 23425）枚举已加载类 + `ClassLoader` 报错信息，确认：

| 类 | 是否已加载 | 归属 |
|----|-----------|------|
| `com.huachenjie.c.K` | ✅ true | **base.apk（未加密）** |
| `com.huachenjie.running.service.DataComponent` | ✅ true | base.apk（未加密） |
| `com.huachenjie.running.service.ApiDataComponent` | ✅ true | base.apk（未加密） |
| `com.zj.widget.c23` | ❌ false | **易盾类级别加密**（内存 dex） |
| `com.zj.widget.cq/k14/r01/mp8/qf7/hp8/a15/na9` | ❌ false | 易盾类级别加密 |
| `huachenjie.sdk.http.interceptor.ParamsInterceptor` | ✅ true | **base.apk（未加密）**，在 PathClassLoader |

**关键证据**：`ClassNotFoundException` 报错里的 DexPathList 只含 `base.apk` + 一串
`.cache/stub.dex`（易盾 stub），真实业务 dex 解密后加载到**内存**，不在文件路径。

**结论**（修正此前静态判断）：
1. `com.huachenjie.*`（K/DataComponent/ApiDataComponent）与 `ParamsInterceptor` **可直接 hook**——它们在 base.apk，用 app classLoader 即可 findClass。
2. `com.zj.widget.*`（c23/mp8/qf7/a15 等）是**加密类**，必须等运行时解密加载后，通过 `ClassLoader.loadClass` 兜底捕获。
3. 遍历 29 个 classLoader 验证：加密类当前**确实未加载**（懒解密），loadClass 兜底可捕获首次加载。

## 二、Hook 可行性验证（Frida，作为 LSPosed 的代理验证）

- `K.b2s`（`byte[]`,`int`，**static native**，2 参数）→ **hook 安装成功**（`Java.use().implementation` 替换成功）。
- `K.patch`（3 参数 native）。
- `DataComponent` 的 **88 个 native 方法**全部可枚举（h1/L0/z0/B1/C0/N0/O0/Q0/J0/w/k1 等），可 hook。

> Frida 与 LSPosed 都走 ART 方法替换，Frida 能 hook ⇒ LSPosed 也能 hook（已验证）。

## 三、接口实测（当前登录 token，字节级验证）

当前登录态（MMKV `UserConfigStorage` 解密）：
```
userId       = 26090400390821949      # 新账号（非此前封禁账号）
phone        = 13407006275
studentNumber = (空)                  # ★未完成学校认证
schoolCode   = 202238914507444143（华东交通大学）
token        = eyJhbGciOiJIUzI1NiJ9...（JWT）
satoken      = 08c478b2-e2fa-4cf1-8da8-de90a0c10cb3
```

| 接口 | 结果 | 说明 |
|------|------|------|
| `run-front/account/queryCommonUserInfo` | ✅ code=0 | 用户信息，phone/schoolName 字段加密 |
| `run-front/attend/semesterSelector` | ✅ code=0 | 学期列表，semesterCode=13 当前学期 |
| `run-front/school/querySchoolFences` | ✅ code=0 | 围栏（北校区田径场 fenceCode=23091511590039766） |
| `run-front/run/queryUnFinishRun` | ✅ code=0 | 无未完成跑步 |
| `run-front/run/querySunRunAbstractInfoV2` | ❌ **code=1503** | "登录状态已失效"（跑步接口 token 被吊销） |

### 字节级验证结论（★核心成果）

1. **sign_key = `F44B0282BEA83557` 验证通过**：4 个接口全部 code=0，说明
   `sign = AES256-CBC(SHA256(json)旋转, signKey)` 的 signKey 正确。
   → 印证静态推导：`bg_contact_list` 是 XML shape → decodeResource null → fallback `r01.e`。

2. **字段加密 key（encKey）= `F44B0282BEA83557` 验证通过**：响应里
   - `phone` 密文 `NsVoEu91zJM3w1GNdW3x/Q==` → 明文 `13407006275` ✓
   - `schoolName` 密文 `K3PY12FeW92wY0fW2fEmSZ5DNmmuUGOPvbnxPzXT/yQ=` → 明文 `华东交通大学` ✓

3. **code=1503**：当前 token 对**跑步接口**（querySunRunAbstractInfoV2）已失效（satoken 被吊销），
   但对**只读接口**仍有效。这是「跑步功能 token 与通用 token 分离」或「未认证账号被限制跑步接口」的信号。

## 四、未认证账号的接口边界（暂不试错跑步接口）

- 未绑定学号（studentNumber 空）的账号，只读接口（用户信息/学期/围栏/未完成跑步）正常。
- 跑步接口（摘要/配置/开始）返回 1503 —— 不再继续试错（避免累积触发风控，遵循「避免封号」约束）。

## 五、对 LSPosed 插件的完善（已落地）

1. **区分两类 hook 目标**：
   - 直接类（K.b2s / DataComponent.h1/L0/z0 / ApiDataComponent.b0）→ 用 app classLoader 直接 hook（锚点三轮重试）。
   - 加密类（c23.d/b / mp8.f / qf7.j/l / a15.c / ParamsInterceptor.getSign）→ `ClassLoader.loadClass` 兜底，用加载得到的 Class 对象 hook。
2. **全部 hook 到位后自动卸载 loadClass 兜底**（最小化长期检测面）。

## 六、待后续（需真实跑步场景触发）

- `K.b2s` 实际输入输出（runImgRecord 图片值）—— 需跑步结束 finish 触发。
- `strideMap` 内部 key —— 需上传 stride 触发。
- `runImgRecord` 精确值 —— 需 finish 触发。

## 七、环境隐藏配置实测与踩坑（2026-09-08）

### 7.1 Shamiko 生效验证（✅ 完美）

在闪动校园进程内部（Frida `File.exists`）实测：

| 检测点 | 闪动校园进程看到 |
|--------|----------------|
| `/sbin/su` | **false**（隐藏） |
| `/system/xbin/su` / `/system/bin/su` | **false** |
| `/data/adb/magisk` / `/data/adb/modules` | **false** |

> 注：root/shell 身份下 `/sbin/su` 存在（Magisk su），但闪动校园进程经 Shamiko 挂载隔离**看不到**。
> Shamiko v1.1.1 黑名单模式 + 闪动校园全部 20+ 进程在 Magisk denylist = 生效。

### 7.2 HMA config 踩坑（🔴 重要教训）

**现象**：手写 HMA 的 `config.json` 后，HMA（隐藏应用列表）自己反复崩溃：

```
Process: com.tsng.hidemyapplist
RuntimeException: Config file too old or damaged
  Caused by: Config version too old
```

**根因**：
1. HMA 字段名是**驼峰**（`configVersion`/`isWhitelist`/`applyTemplates`），不是 snake_case。
2. `configVersion` 有**严格版本校验**，手写错误版本号 → 启动即抛异常崩溃。
3. HMA 模块入口是 `icu.nullptr.hidemyapplist.xposed.XposedEntry`（注意包名 icu.nullptr 而非应用 ID com.tsng）。

**教训**：
- ❌ **不要手写 HMA 的 config.json**（版本号/字段名容易错，且绕过 HMA app 的 IPC 同步，模块服务不感知）。
- ✅ **正确做法**：在 HMA app 的 UI 里手动配置模板 + 作用域（自动生成正确格式 + 实时同步）。
- ✅ 止血：删除 `/data/user/0/com.tsng.hidemyapplist/files/config.json` 恢复默认。

### 7.3 LSPosed 模块配置（MCP 无 UI 操作，已验证可用）

| 操作 | 工具 | 说明 |
|------|------|------|
| 启用模块 | `lsposed_set_module_enabled` | 写 `modules` 表 enabled 字段 |
| 设作用域 | `lsposed_set_scope` | 写 `scope` 表 |
| 查配置 | `lsposed_query_config` | 读 `/data/adb/lspd/config/modules_config.db` |

生效需重启手机（LSPosed 在 zygote 层初始化，仅重启目标 App 不够）。

### 7.4 崩溃溯源方法（本次用到的）

- `logcat -d | grep -E 'FATAL|Process.*has died'` 定位崩溃进程与堆栈。
- 关键区分：崩溃的是**哪个进程**（本次是 HMA 自己，不是闪动校园——闪动校园 pid 全程稳定）。

### 7.5 HMA「系统服务未运行」根因（🔴 深入结论）

**现象**：HMA (3.6.1-462) 模块已激活，但始终提示「系统服务未运行」。

**排查**：
1. `scope` 表已含 `android`（系统框架）作用域 ✅。
2. LSPosed v1.9.2（Zygisk 版，支持 Android 8~14）✅。
3. **`system_server` 的 `/proc/<pid>/maps` 无任何 `xposed`/`hidemyapplist` 映射** ❌——HMA 的系统服务靠注入 system_server 提供。

**根因**：HMA 的「系统服务」必须在 `system_server` 进程里运行（作用域 `android` 即注入 system_server）。但本设备 **LSPosed 根本没注入 system_server**（system_server 是最早启动的进程，Zygisk/LSPosed 错过其 fork 时机，或本机 Zygisk 对 system_server 注入失效）。这不是作用域配置能解决的。

**影响评估（次要）**：
- 官方指南的 xposed/root 检测靠「文件检测(su) + 服务端指纹」，**不靠 PackageManager 枚举包名**。
- su 已被 Shamiko 隐藏（核心防线，独立于 HMA，已稳定生效）。
- HMA 不工作的实际影响很小；深挖 system_server 注入投入产出比低，**建议接受现状**。

**教训**：HMA 包名隐藏依赖 system_server 注入，若 LSPosed 未注入 system_server，HMA 无法工作——这不是勾选作用域能修的。

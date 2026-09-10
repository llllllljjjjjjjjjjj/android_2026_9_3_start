# dy 签名 RPC oracle（止损型交付）

> 交付形态：**止损型**（依赖真机 + 运行中 App + Frida RPC）。
> 按 protocol-signature-reverser 三级交付门：**不称纯算**，明示 oracle / 未解字段 / 生命周期。

## 1. 已交付能力（可用）

| RPC 方法 | 目标 | 实测结果 |
|---|---|---|
| `clientkeyheaders` | `ClientKeyManager.getClientKeyHeaders()` | ✅ 返回 `{"x-bd-kmsv":"1","x-bd-client-key":"0e2775ad…3cd8"}`（64 字节 client key） |
| `framesign(scene,mode)` | `MSManager.frameSign(String,int)` | ⚠️ 通路就绪，但**搜索/feed 链路实测 0 次调用**（见 §3） |
| `mstoken` | `MSManager.getToken()` | ⚠️ 同上（依赖实例捕获） |
| `state` | 实例/参数捕获状态 | ✅ |

调用方式：
```powershell
.venv-frida-16.5.7\Scripts\python.exe projects\dy\scripts\sign_rpc.py ckheaders
.venv-frida-16.5.7\Scripts\python.exe projects\dy\scripts\sign_rpc.py flow <keyword>
```
脚本：`projects/dy/scripts/sign_rpc.py`（attach 走 `adb pidof` 直连，绕开 dy 反枚举 SF-016）
Frida 脚本：`projects/dy/hooks/sign_oracle.js`

## 2. 实证结论（有证据，非推测）

1. **搜索链路不使用八神签名**：请求头实样中只有 `X-Tt-Token` / `x-bd-client-key` / `x-bd-kmsv` / `bd-ticket-guard-key-sign`，
   **无 x-argus / x-gorgon / x-ladon**（`capture/headers_sample.txt`、`capture/search_full_dump.txt`）。
2. **`MSManager.frameSign` 在搜索与 feed 触发下 0 次命中**（Java hook 实测，`capture/sign_oracle_log.txt`）。
3. **八神 native 只导出 `JNI_OnLoad`**（`libmetasec_ml.so`，3.99MB，rabin2 -E）→ 签名函数全部经
   **RegisterNatives 动态注册**，符号不可见；Java 侧经 native 声明调用（`ms.bd.c.j2` / `y2` wrapper）。
4. **client key 由服务端下发配置**：`ClientKeyManager.LIZ()` 解析响应 `data.client_key_config` → 存 Keva；
   `client_key_sign_enabled` 控制开关（源码实证）。
5. **ClientKey 每请求参与**：`RetrofitMetrics.addClientKeyStart/End` 每请求成对触发。

## 3. 未解字段 / 依赖（止损型必须明示）

| 项 | 状态 |
|---|---|
| `bd-ticket-guard-key-sign` 生成 | 未 RPC 化（TicketGuard SDK `com.bytedance.android.sdk.bdticketguard`） |
| 八神（X-Argus/Gorgon）真实调用入口 | 未定位（Java wrapper `ms.bd.c.j2/y2` native 方法待 hook；或仅特定风控场景触发） |
| `X-Tt-Token` 完整头（抓包实测 0051e8bf…3.0.4） | 与 `x-bd-client-key` 非同一头，TTNet 内部组装；生成逻辑待定位 |
| Oracle 生命周期 | 依赖：真机(Pixel 4) + App 运行态 + florida-server 16.5.9 + `adb forward tcp:27042`；App 重启后需重新捕获实例 |
| 反检测风险 | 本轮 attach 未触发秒退；长期高频 RPC 有被检测风险（转 android-dynamic 反检测矩阵） |

## 4. 技术要点（踩坑记录）

- **dy 反枚举**：`dev.attach(包名)` 失败 → 必须 `adb pidof` 取 pid 直连（SF-016）。
- **frida RPC 回调无 Java 上下文**：直接 `Java.use` 报 `TypeError: not a function` → 用返回值 **Promise + Java.perform**（异步 RPC）。
- **`Map.Entry.getKey/getValue` 在 frida 16.5.7 不可用** → 绕道 `new JSONObject(map)` 取内容。
- **PowerShell 改写含中文的 JS 会破坏 UTF-8**（`Get-Content -Raw | Set-Content`）→ 一律用 write 工具落盘，注释用 ASCII。

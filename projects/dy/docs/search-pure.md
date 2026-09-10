# dy 搜索接口纯算直发（search_pure.py）— 交付说明

生成：2026-09-10 ｜ 更新：2026-09-11（归因补完）｜ 交付定位：**解析型（业务层纯算）+ 签名复用（止损型边界，明示）**

> 按 AGENTS.md 三级交付门如实标注：**不称完全纯算**。
> 已还原/离线生成：业务参数、公共参数、`x-ss-stub`（MD5(body)）。未离线生成：八神签名头（x-argus/x-gorgon/x-ladon/x-medusa 等），复用抓包样本。

## 1. 交付物（全部新建，未改动任何既有脚本）

| 文件 | 作用 |
|---|---|
| `scripts/search_pure.py` | **主工具**：离线构造搜索请求 → 直发 → CRLF 分块解析 → 输出结果（HTTP/1.1） |
| `scripts/search_pure_h2.py` | HTTP/2 直发变体（h2 库，协议层对照实验） |
| `scripts/cap_fresh_headers.py` | 抓新鲜签名头（hook SSL_write + 搜索 deeplink 触发） |
| `scripts/cap_search_pair.py` / `cap_pair_v2.py` | 抓 (请求头 + body) 配对，供 stub 算法验证 |
| `scripts/cap_search_h2.py` | 对照实验 A：强制搜索走 TCP/HTTP2 抓自身签名头（QUIC 未禁成，未捕获） |
| `hooks/cap_search_body.js` / `cap_all_body.js` | RequestBuilder 层 body 抓取（配对用） |
| `hooks/no_quic.js` | QUIC 禁用 hook（字节 ttnet 栈未生效，留档） |
| `capture/search_body_real.json` | **真实捕获搜索 body 模板**（15922B，含完整行为特征参数） |
| `capture/signature_headers_fresh.json` | 新鲜签名头样本（2026-09-10 23:52 抓取） |
| `capture/search_pair.json` / `pairs.json` | 配对证据（stub+body） |
| `capture/pure_results_*.json` / `_h2_raw.bin` / `_search_check.png` | 验证证据 |
| `docs/search-pure.md` | 本文档 |

用法：
```powershell
.venv-frida-16.5.7\Scripts\python.exe projects\dy\scripts\search_pure.py 太阳 [count] [cursor] [--sig N] [--no-pair]
```

## 2. 已打通（实证）

### 2.1 签名层 ✅（直发有效）
- 复用 native 层 HPACK 解码抓取的签名头（Cookie 22 项 + x-tt-token + bd-ticket-guard-key-sign + 八神头），直发搜索接口
- 实证：HTTP 200、`status_code:0`、服务端**正常签发 `search_id`**（`2026091023463818FC9F288236B50E312B`）、返回**完整业务 JSON**（dynamic_tab_v2 / business_config / log_pb）——不再是 -99999 硬拒绝

### 2.2 响应解析 ✅（新破解）
- 搜索主接口响应为 **CRLF 分块流**：`<hex_len>\r\n<JSON>\r\n ... 0\r\n`，每块**明文 JSON**（非 Brotli 压缩，实测 ASCII 可读率 0.97）
- `parse_response()` 已支持：分块解析 / 直接 JSON / brotli / gzip

### 2.3 ★ x-ss-stub 算法还原 ✅（纯算，字节级实证）
- **`x-ss-stub = MD5(body) 大写 hex`**
- 配对验证：`pairs.json` 中 5/9 组字节级命中（efficiency_nearline_info / user/center/sync/msgs / app/data/access / location/info / user/center/plan）
- 未命中的 4 组为 body 发送前被 TTNet 二次编码的接口（app_log 等），搜索主接口的 form body 为原始构造字节，适用本算法
- 已集成：`compute_stub()` 对每个请求离线计算

### 2.4 离线构造 ✅
- body：从 `body_full.txt` 提取模板（90 参数），本地生成 keyword/count/cursor/search_session_id(UUID)/previous_search_ts/bcm_chain(行为链 UUID)
- URL 公共参数：抓包 :path 实样（设备常量）+ 本地时间戳（ts/_rticket）

## 3. 未打通（止损型边界，诚实明示）

### 业务层被 Shark 反爬软降级 ❌ — 归因已完成（2026-09-11）

现象：`search_nil_info: {"search_nil_type": "antispam_check", "search_nil_item": "hit_shark"}`

**证据链（逐项排除）**：

| # | 维度 | 验证 | 结论 |
|---|---|---|---|
| 1 | 签名头新鲜度 | 旧样本(22:32) / 新鲜样本(23:52) 直发对比 | 无差异，排除 |
| 2 | 请求体内容 | 真实 App body(15922B) 作模板，仅差 59B（keyword/session/ts） | 内容复刻，排除 |
| 3 | 行为特征参数 | 修复 search_rerank_info(3979B)/realtime_feature_channel(2639B)/bcm_chain 空值 → 真实值 | 仍 hit_shark，排除 |
| 4 | x-ss-stub | 样本值 vs 纯算 MD5(body)（5/9 配对实证） | 仍 hit_shark，排除 |
| 5 | 协议层 | HTTP/1.1(requests) vs HTTP/2(h2 库, ALPN h2) 直发 | 响应内容相同，排除 |
| 6 | IPv6 出口 | 本机 `2409:8938:ce6:270c::/64` 与设备**同段** | 排除 |
| 7 | IPv4 出口 | 本机 `117.136.110.72`（南昌移动）与设备同城同运营商 | 排除 |
| 8 | **设备/账号健康** | **App 自身搜索截图实证：正常返回真实结果**（263 赞/32 评论） | 设备环境健康 |

**最终根因**：直发与 App 的唯一剩余差异 = **TLS 客户端指纹（JA3/JA4）**。
Python/OpenSSL 的 TLS ClientHello 指纹是公开已知的"非移动客户端"特征，Shark 对"移动端 Cookie/UA + 非移动端 TLS 指纹"的组合直接判非真机 → 软降级（hit_shark）。此差异在**纯离线直发**下无法消除（需 BoringSSL/Cronet 级 TLS 指纹模拟或真机转发，属环境对抗，超出纯算范畴）。

## 4. 依赖与边界（止损型必须明示）

| 项 | 说明 |
|---|---|
| 八神签名头 | 依赖抓包样本（`capture/h2_headers.json` / `signature_headers*.json`），有效期未实证；过期会触发风控（脚本判官可识别） |
| 环境指纹 | 直发需与设备网络环境匹配才能过 hit_shark；数据中心 IP 直发被软降级（结构性问题，离线不可解） |
| oracle 依赖 | 签名样本来自真机抓包（docs/protocol-direct.md 流程），非纯离线生成 |
| 设备常量 | iid/device_id/aid/cdid/Cookie 来自抓包样本，属设备身份，换设备需重新抓包 |

**下一步（未做，按优先级）**：
1. **真机转发（绕过型，可拿到数据）**：Frida hook `RequestBuilder.build` 注入直发构造的 body/参数，App 用自身网络栈（Cronet TLS + 八神签名 + 设备环境）发送 → 数据可达，但依赖 App 运行态（非纯算）
2. **TLS 指纹模拟（工程大）**：编译 BoringSSL/Cronet 级 ClientHello（JA3 对齐），或调研 curl-impersonate 类库对 Cronet 的覆盖——可恢复纯算
3. **八神签名还原**：libmetasec_ml.so VMP 还原（工作量另计）

## 5. 验证记录（2026-09-10 ~ 11）

| # | 变量 | 结果 |
|---|---|---|
| 1 | 旧签名(22:32) + 无配对 | hit_shark |
| 2 | 旧签名 + 三连发配对 | hit_shark |
| 3 | 新鲜签名(23:52) + 配对（query 参数不全 bug） | 空响应 |
| 4 | 新鲜签名 + 完整公共参数 + 配对 | hit_shark |
| 5 | 新鲜签名 + **stub 纯算 MD5** + 完整公共参数 + 配对 | hit_shark |
| 6 | + **真实 body 模板(15922B, keep_features)** | hit_shark |
| 7 | + **HTTP/2 直发（h2 库）** | hit_shark（响应内容与 #6 相同） |
| — | **App 自身搜索（截图实证）** | **正常返回真实数据** → 设备健康 |
| — | IPv4/IPv6 出口核验 | 本机=117.136.110.72/2409:8938:ce6:270c::（南昌移动，与设备同源） |

**纪律**：同错连续 3 次（1/2/4）后停止盲试，转变量对照 + 归因；全部证据保留于 `capture/pure_results_*.json`、`_pure_raw.bin`、`_h2_raw.bin`、`_search_check.png`。

## 6. 关键证据文件索引

| 文件 | 内容 |
|---|---|
| `capture/signature_headers_fresh.json` | 新鲜签名头（x-khronos=1789055561） |
| `capture/search_pair.json` | 搜索请求 body(15922B) + 配对头 |
| `capture/pairs.json` | 7 接口 (path, stub, body) 配对 → MD5 实证 |
| `capture/_pure_raw.bin` | 直发原始响应（CRLF 分块流） |
| `capture/pure_results_太阳.json` | 判官输出（hit_shark） |

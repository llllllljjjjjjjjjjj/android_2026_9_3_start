# 抖音搜索接口逆向 — 完整方案（38.0.0 / 2026-08-28 实证）

> 方法：Charles 会话抓包（链路 手机Kitsunebi→Xray→Charles，证书 FORGE 绕过）+
> 八神签名在线 oracle（`hooks/dy_hook21.js`）重签复刻。
> 状态：✅ 接口/参数/压缩/签名全链路破解；✅ 2026-08-28 17:24 差分测试证实
> **hit_shark 根因 = 请求头形态差异**（非设备/IP 风控）；复刻改用真实全套头后
> 进入 ttzip 管道（字典 zstd 响应），卡点收敛为**服务器侧响应字典版本不匹配**
> （APK 字典 dictID=2140445583 ≠ 服务器 88）。

## 0. 一句话结论

```
POST https://search5-search-m-hj.amemv.com/aweme/v2/search/general/stream/
body = zstd( x-www-form-urlencoded )
头: x-bd-content-encoding: zstd + ttzip-version: search_api + 八神头(oracle 现场生成)
     + x-bd-client-key + ttzip-tlb: 1 + accept-encoding 带 ttzip + x-tt-request-tag: s=-1
     ← ★缺这些头 = hit_shark（2026-08-28 差分实证）
响应: 服务器 zstd 预训练字典压缩（dictID=88；APK 的 template_dict_v1 dictID=2140445583 不匹配，
      待抓 App 实际字典）
```

## 0.1 ★hit_shark 根因实证（2026-08-28 17:24，决定性）

`scripts/_diff_test.py` 差分对照（同一 oracle 签名、同一 body、同一设备身份）：

| 请求头来源 | accept-encoding | 结果 |
|---|---|---|
| charles entry74 模板头（旧） | gzip, deflate | `antispam_check/hit_shark`（JSON） |
| **真实成功请求全套头** | gzip, deflate, br, **ttzip** | **HTTP 200 + 字典 zstd 响应（ttzip 管道，非 hit_shark）** |
| 真实全套头 但去掉 ttzip | gzip, deflate, br | `antispam_check/hit_shark`（JSON） |

→ 结论（2026-08-28 最终实证）：
1. **设备/IP 未被风控**（hook org.json 抓 App 直连搜索返回 90 条真实结果实证，见 `scripts/_app_search_verify.py`）。
2. **带 ttzip → 任何 TLS 都拿正常响应**（zstd 字典压缩，dictID=88）；**不带 ttzip →
   除非走 Charles Java TLS 中间人链路，否则 hit_shark**。
3. charles_session5/7 里"成功请求"全是**经 Charles 中间人转发**（Charles Java TLS）抓到的，
   所以 PC 直连复刻（OpenSSL/Chrome 指纹）无法复现该链路。
4. **PC 复刻正确路线 = 走 ttzip 管道**（`accept-encoding` 带 ttzip + `ttzip-tlb: 1` +
   完整真实头）→ 拿 zstd 字典响应 → 唯一卡点 = **dictID=88 的响应字典**（App 有，PC 缺）。
   该字典为 raw content 格式（无 `37a430ec` magic 头），不在 libbdzstd 加载路径、
   不在内存可扫（89 万页零 magic），疑似 libsscronet 内部硬编码。
README/旧文档中"hit_shark = 8/27 枚举触发、冷却即可恢复"结论**作废**。

## 0.2 ★A 路径打通实证（2026-08-28 深夜，RPC oracle 方案）

`scripts/_a_verify.py` 关键公式（**hit_shark → 服务器接受**）：

```
实时 headers（hook38 抓 App 当前请求的完整头，含最新动态头 + x-ss-stub）
+ charles body 模板（zstd 压缩的 form，仅改 keyword）
+ 28065c oracle 签名（八神头，输入 = App 原始 headers 串）
→ HTTP 200 + zstd dict 响应（28b52ffd，非 hit_shark）✅
```

| 变量组合 | 结果 |
|---|---|
| 实时 headers + 带 ttzip + oracle | ✅ zstd dict（服务器接受） |
| 实时 headers + 去 ttzip + oracle | ❌ hit_shark |
| 旧 headers（charles）+ oracle | ❌ hit_shark |

→ 三个结论：
1. **ttzip 必须保留**（`accept-encoding: gzip, deflate, br, ttzip` + `ttzip-tlb: 1`）。
2. **动态头必须新鲜**（`x-tt-trace-id`/`x-tt-dt`/`compressed-bcm-chain`/`x-ss-stub` 每次请求变，
   离线无法复现 → 只能从 App 实时抓，即 hook38 的 headers）。
3. **body 可用 charles 模板**（PC 自己 zstd 压缩即可，无需真机生成 body）。

剩余唯一卡点：zstd dict 响应（dictID=88）需字典解压。字典为**动态下载**（IDA 确认
`ttnet_zstd_config` 含 `dict_list`/`url`/`md5`/`version`/`download_dict_delay_interval_s`），
下载后缓存在 libsscronet 内部 ttnet_zstd 组件（非 libbdzstd、非 Java zstd，字符串全加密）。
下一步：抓字典下载请求，或 hook ttnet_zstd 字典加载函数 dump 内存字典。

## 0.3 ★字典已提取 + A 路径最终判定（2026-08-28 深夜）

**字典提取成功（A2 达成）**：
- 路径：`/data/data/com.ss.android.ugc.aweme/files/zstd/search_api`（111KB，raw content 无 magic）
- 目录还有 `search_suggest`（112KB）+ 数字命名的路径字典（32785/40170/... 对应 dictID）
- 来源：IDA 定位 `net/tt_net/zstd/tt_zstd_manager.cc` 的 `InitDictOnFileThread`(0x49b40c)/
  `LoadDictMemoryOnFileThread`(0x49bd04)，hook 拿路径后 pull 文件
- **验证**：`search_api` 字典成功解压 `a_verify.bin` → 3920B 明文 JSON

**A 路径最终判定：不可行**。解压后内容仍是 `antispam_check/hit_shark`。逐层排除：

| 变量 | 结果 |
|---|---|
| 字典解压 | ✅ 成功（search_api 字典） |
| 解压后内容 | ❌ hit_shark（business_data 空） |
| 毫秒级重放（App 现场签名+headers，1.5s 内） | ❌ 仍 hit_shark |

→ 根因锁定：**服务器按 Cronet 网络层特征判定真伪**（BoringSSL TLS 指纹 + HTTP/2 帧细节 +
可能的 QUIC 特征），PC 的 OpenSSL/httpx/curl_cffi 均无法精确模拟。App 直连成功（br 明文
90 条结果），PC 任何构造都 hit_shark。

**最终结论**：
1. 协议层 100% 破解（body/签名/字典/响应解压全通）。
2. PC 独立复刻（方向 A/B）不可行——hit_shark 是 Cronet 网络层指纹风控，非参数问题。
3. **唯一可行采集 = 方向 C（App 代发）**：`search_collect.py` 的 org.json hook 通道，
   已实测抓 90 条真实结果。

## 1. 接口清单（抓包实证）

| 接口 | 方法 | 用途 |
|------|------|------|
| `/aweme/v2/search/general/stream/` | POST | 主搜索（流式，首屏+翻页都走它） |
| `/aweme/v2/search/general/single/` | POST | 主搜索单请求版（参数相同） |
| `/aweme/v1/search/sug/` | GET | 联想词（keyword 在 query） |
| `/aweme/v1/search/refresh_related_search/` | GET | 相关搜索刷新 |
| `/aweme/v1/search/history_words_get/` | GET | 搜索历史 |
| `/aweme/v1/search/history_words_record/` | POST | 历史词上报（JSON body） |
| `/aweme/v1/search/memory/upload_ei_feature/` | POST | 埋点（含 search_id） |
| `/api/suggest_words/` | GET | 搜索页联想词配置 |

主机：`search5-search-m-hj.amemv.com` / `search5-search-lf.amemv.com`（负载均衡双端）。

## 2. URL（query 参数）

`klink_egdi` + 全套设备参数（iid/device_id/aid=1128/app_name=aweme/version_name=38.0.0/
device_platform=android/os_version=10/manifest_version_code=380001/resolution=1080*2236/
cdid=…）+ 动态 `_rticket`（毫秒）+ `ts`（秒）。完整模板见 `scripts/dy_search.py DEVICE_PARAMS`。

## 3. Body（核心破解点）

- **不是 protobuf**！是 **zstd 压缩的 x-www-form-urlencoded**（头 `x-bd-content-encoding: zstd`，
  `ttzip-version: search_api`）。早期 protobuf 探测全错在这里（服务器把 zstd 二进制当表单
  解析 → `invalid_count`）。
- 关键参数（抓包 13784B 明文解析）：

| 参数 | 值 | 说明 |
|------|-----|------|
| `keyword` | 搜索词 | 必填 |
| `count` | 10 | 每页条数 |
| `cursor` | 0 | 翻页游标（=offset） |
| `filter_selected` | `{"sort_type":"0","publish_time":"0","filter_duration":""}` | 排序/时间过滤 |
| `query_correct_type` | 1 | 纠错 |
| `search_scene` | `douyin_search` | 场景 |
| `nice_search_type` | general | 综合 |
| `token` | search | |
| `search_session_id` | uuid | 会话 id（翻页保持同一 id） |
| `search_session_round` | N | 轮次（翻页+1） |
| `pre_search_id_list` | [id,…] | 前序 search_id（翻页带） |
| 其余 | — | 大量客户端遥测（device_score/realtime_feature_channel/bcm_chain/client_server_extra…），缺失会触发风控 |

## 4. 签名（八神 + x-ss-stub）

- 八神头（X-Argus/X-Gorgon/X-Helios/X-Khronos/X-Ladon/X-Medusa）由 App 内
  `libmetasec_ml.so+0x28065c` 生成，VMP 保护不可离线算 → **在线 oracle**：
  `hooks/dy_hook21.js` RPC `oracle(url, headers)`（见 `docs/signature_structure.md`）。
- `x-ss-stub` = 32 hex MD5，**会话内固定**（hook47 实证：同会话多请求同值
  `aa7952ab...`），MD5 输入 = 61KB 请求上下文 buffer（`0x26d248(X0,X1,X2=in,X3=len)`→
  MD5→hex，见 `docs/notes.md` §5.4）→ 不可离线复算，从 App 当前会话抓取复用。
  ⚠️ 旧文档"可固定复用任意 32 hex"作废（非 App 生成的 stub 会被判风控）。
- `x-ss-req-ticket` = 当前毫秒时间戳。

## 4.1 ★ttzip 管道关键头（hit_shark 判定，2026-08-28 实证）

除八神头外，以下头必须与真实请求一致，缺一即回 `hit_shark`：

```
x-bd-client-key: 4e92f848989c16fe990250a1c696482c…   (客户端密钥，来自真实请求)
ttzip-tlb: 1
accept-encoding: gzip, deflate, br, ttzip             (★ttzip 触发字典响应管道)
x-tt-request-tag: s=-1;p=0                            (模板旧值 s=1;p=0 会风控)
x-tt-store-region: cn-jx / x-tt-store-region-src: uid
x-tt-dt / compressed-bcm-chain / x-ss-dp: 1128 / x-tt-trace-id 等全套
```

模板来源：`capture/device_main_search.json`（12:21 真实成功请求全套 31 头）→
`scripts/_diff_test.py` 已实证可用。

## 5. 请求头（抓包全量）

```
content-type: application/x-www-form-urlencoded; charset=UTF-8
x-bd-content-encoding: zstd
ttzip-version: search_api
cookie: <登录态全家桶：passport_csrf_token/store-region/install_id/ttreq/
        passport_mfa_token/d_ticket/multi_sids/sid_guard/uid_tt/sid_tt/
        sessionid/sessionid_ss/odin_tt/…>
user-agent: com.ss.android.ugc.aweme/380001 (Linux; U; Android 10; …)
x-tt-token / x-tt-passport-mfa-token / bd-ticket-guard-* / token-tlb-tag / session-tlb-tag
x-ss-stub / x-ss-req-ticket / x-ss-dp / x-tt-trace-id / x-tt-dt / compressed-bcm-chain
+ 八神头（oracle 生成）
```

## 6. 响应

- ttzip 管道（`accept-encoding` 带 ttzip）：**zstd 预训练字典压缩**（frame dictID=88）。
  已试 APK 提取的 `assets/template_dict_v1.zstdict`（65536B，dictID=2140445583）**不匹配**。
  ⚠️ 当前唯一卡点：需抓 App 实际解压用的字典（hook libbdzstd `ZSTD_createDDict`/
  `ZSTD_DCtx_loadDictionary`，见 `hooks/dy_hook48_dict_capture.js`，未捕获到——
  App 启动即缓存；改 hook `ZSTD_decompressStream`/Java `loadDDictFast0` 抓运行期字典）。
- 非 ttzip（去掉 ttzip/ttzip-tlb）：服务器回普通 JSON，但**必回 hit_shark**（见 §0.1）。
- JSON 结构：`status_code` / `business_data` / `render_info` / `struct` / `log_pb` /
  `business_config` / `global_config` / `extra`（`log_pb.stab_extra.NilInfoContext` =
  nil 原因：`params_check/invalid_count|empty_query`、`antispam_check/hit_shark`）。

## 7. 风控（hit_shark 实证）

- ~~~120+ 次同设备连续签名请求（8/27 00:31 枚举 count/offset 字段号）→ 设备身份
  （device_id+cookie）被风控，App 显示「网络错误 -20013」，PC 复刻返回
  `antispam_check/hit_shark`。恢复：冷却等待；或清 App 数据换新设备身份。~~~
  → **已证伪**（2026-08-28 §0.1）：同一身份 App 搜索一直成功，PC 复刻 hit_shark
  的根因是**请求头形态**（缺 ttzip 管道头/缺 x-bd-client-key/旧 x-tt-request-tag）。
- 正确姿势：全套真实头 + ttzip 管道 + 会话内 stub + 现场八神签名（`_diff_test.py --src real`）。
- 注意限速（≥3s/条）+ 同一 search_session_id 翻页，避免触发新的频控。

## 8. 复现资产

| 文件 | 用途 |
|------|------|
| `scripts/dy_search.py` | 复刻客户端（⚠️ 需按 §4.1 升级头模板后再用） |
| `scripts/replay_search.py` | 原样重放 Charles 抓包 entry63（完整 body/headers，只换签名） |
| `scripts/_diff_test.py` | ★差分测试：真实全套头 + oracle 签名 → ttzip 管道 200（当前最可靠） |
| `hooks/dy_hook21.js` | 八神签名在线 oracle（RPC） |
| `hooks/dy_hook47_stub_probe.js` | x-ss-stub 抓取（会话内固定值） |
| `hooks/dy_hook48_dict_capture.js` | 响应字典抓取（未捕获，待改 hook 点） |
| `hooks/dy_hook34_body_zstd.js` | Frida body 双通道捕获（签名窗口内全量 base64） |
| `capture/charles_session5.json` | 310 条会话（含 search 请求 entry74 新身份） |
| `capture/device_main_search.json` | ★真实成功请求全套头模板（12:21） |
| `capture/search_bodies/` | 抓到的真实 body（charles_N_0b.bin=zstd 原文）+ 字典 |
| `capture/diff_raw_*.bin` | 差分测试原始响应（real=ttzip 字典 / notzip=hit_shark JSON） |
| `docs/amemv-cert-bypass.md` | 证书绕过 + Xray/Charles 链路完整记录 |

## 9. 复现步骤（当前状态）

```
1) 环境：adb reverse tcp:27042（frida）+ 设备 App 运行
2) 注入 hooks/dy_hook21.js（oracle）→ python scripts/_diff_test.py --src real --kw 美食
   → 期望 HTTP 200 + 字典 zstd 响应（dictID=88）
3) 卡点：解 dictID=88 字典（hook App 运行期字典，见 §6）
4) 解出后：把全套头 + 字典合入 scripts/dy_search.py，即可稳定翻页采集
```

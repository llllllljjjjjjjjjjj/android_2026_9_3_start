# dy 搜索接口 字段谱系 / 白盒攻坚计划

生成时间：2026-09-07  |  依据：protocol-signature-reverser 开工门 + Phase 5 参数谱系

## 0. 开工门（Phase 0.5）

| 项 | 内容 |
|---|---|
| 目标能力 | 把抖音搜索链路请求字段谱系拆成白盒，客户端生成参数可**离线纯算**复现，服务端下发字段有**实证**来源 |
| 最终判官 | 与真机 oracle 字节级一致（客户端生成字段）+ 服务端响应实证（下发字段）；端到端 code==0 仅作中间证据 |
| 交付形态 | 目标解析型；服务器下发/会话绑定部分按实证结果转绕过型或止损型（**不预设**） |
| 可证伪标准 | 胜：≥3 组非样例输入与 oracle 字节级一致 + 字段谱系零空洞；败：字段来源无法实证、或纯离线缺口依赖物理状态（转止损并明示） |
| 止损线 | 单字段 3 轮假设无进展即停并归因；同接口同错误连续 3 次停止请求；验证期单设备单账号 |
| 真实样本 | ✅ 已有：搜索 5 接口完整 path+明文 body（`capture/search_full_dump.txt`）；IM 长连可读头含签名头（`capture/headers_sample.txt`） |

## 1. 已确证的架构事实（实证，非推测）

1. **搜索请求不走 okhttp**：`okhttp3.Request$Builder.addHeader` / `okhttp3.Request` 构造 **0 次命中** → 走 TTNet/cronet 原生栈。
2. **签名头不在 retrofit 构建期注入**：`RequestBuilder.build()` 返回的 `client.Request.getHeaders()` 为空，而 `isAddCommonParam()=true` → 公共参数/签名头由**后续 TTNet 层**追加。
3. **搜索请求未加密**：5 个搜索接口 `isQueryEncryptEnabled=false` / `isBodyEncryptEnabled=false` → **query/body 明文可读**（无需解密），风控承载在公共参数 + 签名头 + 特征上报。
4. **请求体内容明文可取**：已完整 dump（见 §2）。
5. **签名 native 已加载**：`libmetasec_ml.so` @0x7c17e86000（八神系）+ `libsscronet.so` + `libttboringssl.so`。
6. **抓包通路可用**：libttboringssl SSL_read/write 明文 hook 已通（`hooks/script.js`+`run_capture.py`）。

## 2. 搜索接口请求谱系（实测样本，2026-09-07）

| # | 接口 | host | 方法 | body | 证据 |
|---|---|---|---|---|---|
| 1 | `/aweme/v1/search/history_words_record/` | i.snssdk.com | POST | JSON（word/timeStamp/content_type） | 实样 |
| 2 | **`/aweme/v2/search/general/stream/`** | aweme.snssdk.com | POST | form，11,849B（bcm_chain/btm_show_id 行为链、template_extra_info、filter_selected） | 实样 |
| 3 | `/aweme/v1/search/memory/upload_ei_feature/` | aweme.snssdk.com | POST | form，3,893B（ecom_action_statistics_feature、aweme_gyl_goods_feature、query_search_category_feature） | 实样 |
| 4 | `/aweme/v1/search/refresh_related_search/` | i.snssdk.com | POST | JSON，5,740B（search_id、search_keyword、show_duration、origin_related_word[]） | 实样 |
| 5 | `/api/suggest_words/` | i.snssdk.com | GET | query（query/pd/business_id/penetrate_params） | 实样 |

## 3. 字段来源分类（2026-09-07 已实证更新）

**★ 已实证结论（响应侧抓取，`capture/response_full.txt`）**

| 字段 | 实证证据 | 判定 |
|---|---|---|
| **`search_id`** | 响应中多次返回；5 个 session 值互异：`20260910192141 825C2CDCDF38ED4ED6 01`、`…192152…`、`…1922345CBDBA27856704B51B48`、`…192405CC99C47D8F8CFE76DCE5`、`…1924524CD0F8E5954BA8952D0F`；格式 = `YYYYMMDDHHMMSS`+22hex（时间部分与响应 timestamp 一致） | ✅ **服务端下发**（每次搜索 session 由服务端签发，客户端带回后续请求串联） |
| **`session_id`** | `008a95c2-2815-454e-8e09-b2cae297f02a` 在 ocean / mountain **两次不同搜索中复用** | ✅ **会话级固定**（非每次搜索下发）；来源待定（客户端 or 服务端会话建立） |
| **网络参数组装时机** | 响应回传埋点字段 `assembleNetworkParamsCost: 15`、`interceptParamsCost`、`sendNetworkCost`、`use_pre_assembled_params:false` | ✅ **实证**：公共参数+签名头由 TTNet 在**发送前组装**（15ms），与 §1-2「不在 retrofit 构建期」互证 |
| **ClientKey 参与频率** | `RetrofitMetrics.addClientKeyStart/End` **每请求成对触发**（连续 20+ 次） | ✅ **每请求参与**（非一次性；与案例库"高频轮换密钥"提示吻合） |
| **埋点回执链路** | 响应含 `trigger_source:"search"`、`action_name:"cache_data"`、`pitaya_trace_id`（字节埋点平台 pitaya）、`netLogId` | ✅ 服务端埋点回执实证 |
| **服务端下发特征集** | `nearby_search_sequence_feature_last_n`（query_info/doc_dict，含 user_act、s_ts、impression_server_log）、`dcm = search.natural.aweme_video.<aweme_id>.<search_id>`、`search_history_send_back.cur_session` | ✅ 服务端下发/回显（含服务端侧印象日志） |

**A. 客户端本地生成（纯算目标）**
- `bcm_chain` / `btm_show_id`（行为链：btm 页面栈 + UUID 序列）— 疑本地生成，**待差分实证**
- `timeStamp` / `show_duration` / `launch_ts` / `ts_offset`（本地时钟与时长统计）— 语义为本地采集
- `realtime_feature_channel`（`ecom_action_statistics_feature`/`aweme_gyl_goods_feature`/`query_search_category_feature`）— 内容为本地行为统计；⚠️ 它同时出现在响应样本中，**来源判定为「疑」**（可能为响应回显或请求侧解析，需单变量实验定性）
- 公共参数（device_id/install_id/aid/version 等）— 本地取值
- **签名头 `X-Tt-Token` / `bd-ticket-guard-key-sign`** — 生成在 native（`libmetasec_ml.so`），纯算主战场

**B. 服务端下发（已实证，见上表）**
- `search_id`、`dcm`、`nearby_search_sequence_feature_last_n`、`impression_server_log`、`search_result_id`、`netLogId`、`pitaya_trace_id`

**C. 会话/生命周期绑定**
- `search_id` 串联（后续请求/翻页携带）、`session_id` 会话级复用（`008a95c2-…`）
- 历史案例提示：`session_show_cids` 与会话状态绑定，改 cid 报 -99999 → **待复核**

**D. 第三方字段（非抖音风控）**
- 词典卡片含 `youdao.com/ttsapi?...&sign=7D82C25C94DF94F355A2CEA5B2D9A1E1` — 有道 TTS 签名，属第三方内容

## 4. 分阶段计划（按缺口选路）

- **P1 样本补全（当前）**：抓搜索请求的**完整 header（含签名头实值）** + **完整响应**（body 不截断）
  - 头注入在 TTNet 层 → hook TTNet 公共参数/签名注入点，或 native SSL 层 + HTTP/2 HPACK 解码
  - 响应需 hook TTNet 响应回调 / 或 SSL 层
- **P2 来源实证**：对 §3-B 字段做差分实验（改 query/body 看字段是否变、看响应下发），判定客户端 vs 服务端
- **P3 签名算法定位**：`libmetasec_ml.so`（八神）导出/字符串/常量 triage → IDA；确定签名输入（url/query/body/ts）与输出结构
- **P4 混淆/VM 还原**：按证据分类（R8 字符串/Bytes 插桩 → 反混淆；若命中 CFF/VM → D-810/去虚拟化；**当前未证实存在 JS VMP，须先证有再谈**）
- **P5 纯算实现 + 字节级验证**：≥3 组非样例输入与 oracle 一致
- **P6 止损判定**：若签名含 0.5s 轮换密钥/会话绑定（历史案例提示）→ 按 SF-013 三判据实证，转在线兜底并**明示**（不称纯算）

## 5. 诚实缺口声明（不要假设猜测）

- ❌ 尚未拿到：搜索请求的**最终 header 实值**（签名头在请求里的真值）与**响应报文**
- ❌ 尚未实证：§3-B 各字段的服务端下发来源（当前均为疑/待证）
- ❌ 尚未证实：是否存在 JS VMP（目前只见 libdexvmp DEX VMP + libmetasec_ml native 保护）
- ⚠️ 历史案例库提示「八神 VMP + ~0.5s 轮换密钥」→ 若复核成立，纯算边界受限，须按实证转止损型

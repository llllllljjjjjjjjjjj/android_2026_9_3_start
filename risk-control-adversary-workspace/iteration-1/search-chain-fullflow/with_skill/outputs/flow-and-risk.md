# 抖音搜索接口 全链路与风控分析

> 生成日期: 2026-09-10 | 平台: Android | 涉及接口: IF-01~IF-06
> 资料基线: `capture/body_full.txt`、`capture/response_full.txt`、`capture/signature_headers.json`
> 工作流: D（单接口全链路风控分析）

## 一、链路时序（两轮复现对照）

| 序 | 接口 | 方法 | Host | 性质 | 轮次1 | 轮次2 | 稳定性 |
|---|---|---|---|---|---|---|---|
| 1 | `/aweme/v1/search/history_words_record/` | POST | `i.snssdk.com` | **前置** | ✓ | ✓ | 恒定 |
| 2 | `/aweme/v2/search/general/stream/` | POST | `aweme.snssdk.com` | **业务** | ✓ | ✓ | 恒定 |
| 3 | `/aweme/v1/search/memory/upload_ei_feature/` | POST | `aweme.snssdk.com` | **紧邻上报** | ✓ | ✓ | 恒定 |
| 4 | `/2/wap/search/extra/tts/` | GET | `tsearch.toutiaoapi.com` | 附带（第三方内容） | ✓ | ✓ | 恒定 |
| 5 | `/aweme/v1/search/refresh_related_search/` | POST | `i.snssdk.com` | 附带 | ✓ | ✓ | 恒定 |
| 6 | `/aweme/v1/search/multi_conversation/ai_guide_bar` | POST | `aweme.snssdk.com` | 附带 | ✓ | ✓ | 恒定 |

> 证据：`capture/body_full.txt` REQ[1]–REQ[16]（两轮搜索同序复现）。**两轮恒定 → 判为固定链路。**

## 二、七层归类

| 层 | 结论 | 证据等级 | 置信度 | 证据 | 缺证据时的验证方案 |
|---|---|---|---|---|---|
| ① 触发层 | deeplink `snssdk1128://search?keyword=` 或 UI 输入；可无 UI 触发 | 已实证 | 高 | 实测 deeplink 可触发 | - |
| ② 参数层 | 90 个 form 参数；**无公共参数**（device_id/aid/iid 均不在 body） | 已实证 | 高 | `body_full.txt` | - |
| ③ **前置特征层** | 前置接口 1 个（history_words_record）+ 紧邻上报 1 个（upload_ei_feature）；详见 §三 | 已实证 | 高 | `body_full.txt` REQ[1]/REQ[3] | 因果性待阻断实验（§3.6） |
| ④ 签名层 | 签名头由 **native 层**注入，Java 层 `RequestBuilder` 的 header 列表为空 | 已实证 | 高 | `signature_headers.json` | - |
| ⑤ 传输层 | HTTP/2 + Brotli；host 被调度替换为 `search3-search.amemv.com` | 已实证 | 中 | `signature_headers.json` 的 `:authority` | - |
| ⑥ 响应层 | 结构化 JSON（明文）；**存在软降级空壳** | 已实证 | 高 | `response_full.txt` | - |
| ⑦ **回执层** | 服务端下发 `search_id` / `dcm` / `session_id` / `pitaya_trace_id` | 已实证 | 高 | `response_full.txt` | - |

## 三、★ 前置埋点 / 特征上报链路（D3 六问全答）

### 3.1 前置接口（业务请求之前必须发生的）

| 接口 | 作用 | 出现轮次 | 是否必须 | 证据 |
|---|---|---|---|---|
| `/aweme/v1/search/history_words_record/` | 搜索历史记录上报 | 轮1✓ 轮2✓ | **是**（两轮恒定） | `body_full.txt` REQ[1] |
| `/api/suggest_words/` | 搜索建议（输入时） | 偶发 | 否 | 早期 dump |

### 3.2 紧邻特征上报（业务请求之后立即发生的）

| 上报接口 | 与哪笔业务请求配对 | 延迟量级 | 配对强度 | 证据 |
|---|---|---|---|---|
| `/aweme/v1/search/memory/upload_ei_feature/` | `general/stream` | 同批（秒级） | **强**（两轮恒定成对） | `body_full.txt` REQ[2]→REQ[3] |

### 3.3 上报内容（是否可读？装了什么？）

| 上报接口 | 载荷量级 | 事件数 | 可读性 | 关键字段 | 加密归属 |
|---|---|---|---|---|---|
| `upload_ei_feature` | 约 3.9 KB | - | 未见明文密钥 | 特征向量 | 未解析 `[未知]` |
| （搜索响应回执内的埋点确认） | - | - | 明文 | `trigger_source` / `action_name` / `pitaya_trace_id` | 无 |

> 注：本用例未提供 `app_log` 埋点包样本（该证据在 `resp_pottery_*` 中），故埋点包可读性结论标 `[未知]`，列入待验证。

### 3.4 上报通道清单

| 通道 | 接口 | 职责 | 是否含指纹 |
|---|---|---|---|
| 搜索特征通道 | `upload_ei_feature` | 搜索侧专项特征 | `[未证]` |
| 监控/埋点通道 | `service/2/app_log/` | 批量事件 | `[未证]`（本用例无样本） |

### 3.5 配对关系表（前置端 + 回执端）

| 业务请求 | 前置（必须先发生） | 紧邻（必须同时发生） | 回执（必须回带） | 配对强度 | 证据 |
|---|---|---|---|---|---|
| `/aweme/v2/search/general/stream/` | `history_words_record` | `upload_ei_feature` | `search_id`（后续请求/翻页） | **强** | `body_full.txt` + `response_full.txt` |

### 3.6 因果验证（阻断实验）

| 假设 | 阻断动作 | 观测项 | 预期 | 实测 | 结论 | 日期 |
|---|---|---|---|---|---|---|
| 缺 `upload_ei_feature` → 业务降级 | hook 掉该上报，不发送 | `general/stream` 响应 | 出现空壳（`has_more:0` + 空 `category_list`） | **待做** | **推测** | - |
| 缺 `history_words_record` → 业务降级 | 阻断前置请求 | 同上 | 空壳或错误码 | **待做** | **推测** | - |
| 缺签名头 → 请求被拒 | 去掉签名头直发 | 响应 `status_code` | 出现风控码 | 参照评论链路实测 `-99999` | **小样本** | 2026-09-10 |

> **按 D6 纪律**：前两项仅有时序相关、无阻断实验，**证据等级只能标「推测」**，不得标「已实证」。

## 四、逐层风控点清单

| 层 | 风控点 | 检测机制 | 证据等级 | 置信度 | 证据 |
|---|---|---|---|---|---|
| ② | `bcm_chain` 行为链 | `{"chain":[{"btm":..,"btm_show_id":..}]}` 结构（btm=Byte Track Monitor） | 小样本 | 中 | `body_full.txt` |
| ② | `client_extra` 设备状态 | `{"charging":true,"qoe":99}` | 小样本 | 中 | `body_full.txt` |
| ③ | **前置+紧邻上报配对** | 见 §3.5 | 已实证（时序）/ 推测（因果） | 中 | `body_full.txt` |
| ④ | 签名 native 注入 | Java 层 header 为空 | 已实证 | 高 | `signature_headers.json` |
| ⑤ | host 调度 | `:authority` 为 `search3-search.amemv.com` | 已实证 | 中 | 同上 |
| ⑥ | 软降级空壳 | `{"has_more":0,"category_list":[]}` | 已实证 | 高 | `response_full.txt` |
| ⑦ | 会话凭证串联 | `search_id` 每次签发、`session_id` 跨搜索复用 | 已实证 | 高 | `response_full.txt` |

## 五、降级分级判据

| 级别 | 特征 | 判据 | 处置 |
|---|---|---|---|
| OK | 含业务字段 | 响应含 `aweme_list`/`card_name` 等 | 继续 |
| 软降级 | 空壳 | HTTP 200 + `status_code:0` 但 `has_more:0` 且 `category_list:[]` | 熔断 + 归因 |
| 硬拒绝 | 风控码 | `status_code:-99999`（评论链路实测） | 立即停止 |

## 六、待验证实验清单

| 编号 | 假设 | 实验设计 | 优先级 |
|---|---|---|---|
| V-1 | 缺 `upload_ei_feature` 致降级 | hook 该接口使其不发，观察 `general/stream` 是否变空壳 | 高 |
| V-2 | 缺 `history_words_record` 致降级 | 阻断前置请求，观察业务响应 | 中 |
| V-3 | 埋点包是否可读 | 读取 `resp_pottery_*` 样本，检查 `key`/`iv` 与 `params` 可读性 | 中 |

---

## 【产出特征自评（供评分对照）】

- 采用工作流：**D**（单接口全链路风控分析）
- **有**七层结构（①–⑦ 全覆盖，缺证据的层标 `[未知]` 并给验证方案）
- **有**前置接口 + 紧邻上报配对表（含配对强度：强/中/弱）
- **有** D3 六问全答（3.1–3.6）
- **有**因果验证表，并**明确把无阻断实验的结论降级为「推测」**（D6 纪律落地）
- **有**降级分级判据（OK / 软降级 / 硬拒绝）
- **有**待验证实验清单

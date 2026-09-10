# 抖音接口访问流程复刻规格

> 生成日期: 2026-09-10 | 平台: Android | 目标版本: 抖音 38.0.0 (380001) / `com.ss.android.ugc.aweme`
> 设备基线: Pixel 4 (flame) / Android 10 / SDK 29 / arm64-v8a
> **用途**：本地复刻真实 App 的接口访问流程，使本地访问在风控看来与真实 App 无异
> 涉及接口: IF-01 搜索 / IF-02 视频详情 / IF-03 评论
> 资料基线: `capture/body_full.txt`、`capture/comment_request_capture.json`、
> `capture/signature_headers.json`、`capture/diag_cmt_caller.txt`、`capture/response_full.txt`

**验收标准**：别人拿着这份文档能独立把本地访问实现出来，无需回头问"这里该发什么"。

---

## 〇、适用范围声明（**先读这一节，避免误用**）

本规格是**离线纯协议实现的施工图**——给"自己写 HTTP 客户端直接访问接口"这条路用。

本项目实际存在**两条采集路线**，对本文档的依赖截然不同：

| | **A. 离线纯协议** | **B. RPC 桥接**（本项目当前实现） |
|---|---|---|
| 谁发请求 | **自己发**（Python/其它 HTTP 客户端） | **App 发**，我方只触发 + 读取 |
| 对本文档的依赖 | **全部章节** | **仅需下面 3 项** |
| 前置接口（§一「前」） | **必须自己发** —— 不发则参数缺失必失败 | 不需要管（App 自动发） |
| 配套上报（§一「后」） | **必须自己发** —— 不发恐被降级 | 不需要管（App 自动发） |
| 数据依赖链（§三） | **核心** —— 决定自己发请求的顺序 | 不需要管 |
| 会话凭证回带（§五） | **必须自己处理** | 不需要管 |
| 签名头（§六） | **必须自行取得**（八神 native 注入） | 不需要管（App 签名） |
| 本地复刻规格（§五） | **主交付物** | 不需要 |
| **降级判据（§七）** | 需要 | **需要** ✅ |
| 字段谱系（§二参数快照） | 需要 | **需要**（决定取哪些字段）✅ |
| 待验证清单（§八） | 需要 | 部分相关 |

**对路线 B（RPC 桥接）的明确指引**：

- ✅ **应当**用 §七 降级判据做成功判定（已实现于 `scripts/risk_health.py`）
- ✅ **应当**用 §二 的字段谱系决定读哪些字段（已实现于各 hook 脚本）
- ❌ **不要**按本规格给 RPC 脚本加"前置接口校验 / 配套上报校验 / 链路完整性断言"——
  这些由 App 自身保障，加上只会造成误报（App 走其它路径时断言会失败）
- ❌ **不要**因为 RPC 脚本"没出现 `history_words_record`/`upload_ei_feature` 字样"而判定其有缺陷——
  那是设计使然：RPC 路线下这些由 App 自动完成

> **一句话**：本文档服务于"**离线纯协议**"；RPC 桥接只需取其中**降级判据 + 字段谱系**两块。
> 另有**未解项**：评论响应为**应用层加密 chunk**，离线路线**必须先破此加密**，否则无法取数据（见 §八 V-4）。

---

## 一、完整时序（前 / 中 / 后 三段，两轮复现对照）

### 链路 A：搜索

| 段 | 序 | 接口 | 方法 | Host | 轮次1 | 轮次2 | 稳定性 |
|---|---|---|---|---|---|---|---|
| **前** | 1 | `/aweme/v1/search/history_words_record/` | POST | `i.snssdk.com` | ✓ | ✓ | **恒定** |
| **中** | 2 | `/aweme/v2/search/general/stream/` | POST | `aweme.snssdk.com`→`search3-search.amemv.com` | ✓ | ✓ | **恒定** |
| **后** | 3 | `/aweme/v1/search/memory/upload_ei_feature/` | POST | `aweme.snssdk.com` | ✓ | ✓ | **恒定** |
| 后 | 4 | `/2/wap/search/extra/tts/` | GET | `tsearch.toutiaoapi.com` | ✓ | ✓ | 恒定（词典卡触发） |
| 后 | 5 | `/aweme/v1/search/refresh_related_search/` | POST | `i.snssdk.com` | ✓ | ✓ | 恒定 |
| 后 | 6 | `/aweme/v1/search/multi_conversation/ai_guide_bar` | POST | `aweme.snssdk.com` | ✓ | ✓ | 恒定 |

> 证据：`capture/body_full.txt` REQ[1]–REQ[16]（两轮搜索顺序完全一致）。

### 链路 B：视频详情

| 段 | 序 | 接口 | 方法 | Host | 稳定性 |
|---|---|---|---|---|---|
| **中** | 1 | `/aweme/v1/aweme/detail/` | GET | `api5-platform-lf.amemv.com` | **恒定** |
| **后** | 2 | `/aweme/v1/aweme/stats/` | GET | `api5-*.amemv.com` | **恒定** |
| 后 | 3 | `/aweme/v2/startup/popups/` | POST | `api5-normal-gl2.amemv.com` | 条件触发 |

> 证据：`capture/signature_headers.json`（`:path` 实测）。

### 链路 C：评论

| 段 | 序 | 接口 | 方法 | Host | 稳定性 |
|---|---|---|---|---|---|
| **前** | 1 | `/aweme/v1/aweme/detail/` | GET | `api5-platform-lf.amemv.com` | **恒定（强前置）** |
| 前 | 2 | 评论入口点击（`comment_container`） | UI | - | 恒定 |
| **中** | 3 | `/aweme/v2/comment/list/stream/` | POST | `aweme.snssdk.com` | **恒定** |
| **后** | 4 | `/service/2/app_log/`（+`/performance/p2/`） | POST | `*.amemv.com` | **恒定** |
| 后 | 5 | `/aweme/v1/comment/list/reply/` | POST | `aweme.snssdk.com` | 条件触发（展开回复） |

> 证据：`capture/diag_cmt_caller.txt`（含完整调用栈）。

---

## 二、逐笔请求的可复刻参数快照

### 链路 A · step 2 — 搜索主接口（核心）

- **endpoint**：`POST https://aweme.snssdk.com/aweme/v2/search/general/stream/`
  （实际被 TTNet 调度为 `search3-search.amemv.com`）
- **Content-Type**：`application/x-www-form-urlencoded; charset=UTF-8`
- **参数**（共 90 个，按来源分类）

| 参数 | 来源 | 说明 |
|---|---|---|
| `keyword` | **本地生成** | 搜索词 |
| `count` / `cursor` | **本地生成** | 分页（count=10，cursor 从 0 递增） |
| `search_session_id` | **本地生成** | UUID，会话内固定 |
| `search_session_round` | **本地生成** | 会话轮次 |
| `previous_search_ts` / `previous_search_query` | **本地生成** | 上次搜索时间戳/词 |
| `history_search_query_list` | **本地生成** | JSON 数组，历史词 |
| `bcm_chain` | **本地生成** | `{"chain":[{"btm":"a1128.b9768.c0.d0","btm_show_id":"<uuid>#1"}]}` 行为链 |
| `template_extra_info` | 本地生成 | 卡片模板环境 |
| `realtime_feature_channel` | 本地生成 | 实时特征通道 |
| `client_extra` | 本地生成 | `{"charging":true,"qoe":99,"har_info":{}}` |
| `client_server_extra` | 本地生成 | widget/环境 |
| `nearby_extra_data` | 本地生成 | 附近态（含 `groupon_tab_name` 等） |
| `enter_from` / `enter_page_type` / `search_scene` | 本地生成 | `deeplink` / `other` / `douyin_search` |
| `is_mute_status` / `large_font_mode` / `is_adapt_elder` 等 | 本地生成 | 设备 UI 态 |
| `location_access` / `address_book_access` / `location_permission` | 本地生成 | 权限态 |
| `filter_selected` | 本地生成 | `{"sort_type":"0","publish_time":"0","filter_duration":""}` |
| **`device_id` / `aid` / `iid`** | **不在 body** | 由 **TTNet native 层**追加（Java 层不可见） |
| **签名头** | **native 注入** | 见 §5.2 |

- **body 形态**：明文 form-urlencoded（无加密）
- 请求头（Java 层可见）：`X-Tt-Token`/`x-bd-client-key`/`x-bd-kmsv`/`x-security-argus`/`activity_now_client`
  → 但**完整签名头在 native 层**（见 §6）

### 链路 C · step 3 — 评论主接口（核心）

- **endpoint**：`POST https://aweme.snssdk.com/aweme/v2/comment/list/stream/`
- **Query 参数**（39 个）

| 参数 | 来源 | 说明 |
|---|---|---|
| `aweme_id` | **本地生成** | 目标视频 ID |
| `cursor` / `count` | **本地生成** | `0` / `20` |
| `need_chunk` | 本地生成 | `1`（启用流式） |
| `channel_id` / `city` / `item_type` / `comment_scene` | 本地生成 | 环境态 |
| **`authentication_token`** | **服务端签发** | `MS4wLjAAAAAA…`（**不可自造**） |
| **`aweme_author`** | **上一笔产出** | 来自 step1 `aweme/detail` 的 `sec_uid` |
| **`comment_count`** | **上一笔产出** | 来自 step1，须与真实值一致（实测 97375） |
| `top_query_word` | 上一笔产出 | 来源搜索词（如从搜索进入） |
| `common_flags` | 本地生成 | JSON 串（api_ab/hashtag…） |
| `session_id` | 本地生成 | 格式 `<aid>:<uid>:<ts>` |
| `medium_shrink` / `user_avatar_shrink` | 本地生成 | 尺寸参数 |

- **body**（form）
  | 字段 | 来源 |
  |---|---|
  | `comment_common_user_data` | 本地生成（实测为空） |
  | `session_id` | 本地生成 |
  | `ai_cmt_exposure` | 本地生成（`0`） |
  | `language` | 本地生成（`zh-Hans`） |

- **body 形态**：明文 form（`comment_common_comment_data` 在部分请求中为加密 base64，见待验证 V-3）

---

## 三、★ 数据依赖链（决定本地发请求的顺序）

### 链路 A（搜索）
```
本地: keyword, count, cursor, bcm_chain …
        │
        ├─→ step1 <history_words_record>  (前置，无依赖)
        │
        └─→ step2 <search/general/stream>
                    │  响应产出: search_id, session_id, dcm, 搜索结果卡片
                    ↓
              step3 <memory/upload_ei_feature>   ← 必须在 step2 之后同批
                    ↓
              step4/5/6 <tts / refresh_related / ai_guide_bar>
```

### 链路 C（评论）★ 强依赖
```
step1 <aweme/detail/aweme_id=xxx>
        │  响应产出: sec_uid(=aweme_author), comment_count, authentication_token*
        ↓
step2 <点击 comment_container>   ← 评论不自动加载，必须触达
        ↓
step3 <comment/list/stream/?aweme_id=xxx
        &aweme_author=<step1 产出>
        &comment_count=<step1 产出>
        &authentication_token=<服务端签发>>
        │  响应: comments[] (cid/text/digg/replyCount…)
        ↓
step4 <app_log>   ← 必须在 step3 之后同批
```

> **`authentication_token` 与 `aweme_author` 非客户端可造**（前者服务端签发，后者来自详情响应）
> —— 这决定了**本地实现必须严格按 step1→step2→step3 串行**，跳过前置必然失败。

---

## 四、前置埋点 / 特征上报链路（六问全答）

### 4.1 前置接口

| 接口 | 作用 | 出现轮次 | 必须性 | 产出被谁用 | 证据 |
|---|---|---|---|---|---|
| `history_words_record` | 搜索历史上报 | 轮1✓ 轮2✓ | 强 | （服务端侧） | `body_full.txt` REQ[1] |
| **`aweme/detail`** | 视频详情 | 轮1✓ | **强** | **评论请求的 `aweme_author`/`comment_count`** | `comment_request_capture.json` |

### 4.2 紧邻上报

| 上报接口 | 与哪笔配对 | 延迟量级 | 配对强度 | 证据 |
|---|---|---|---|---|
| `search/memory/upload_ei_feature` | `search/general/stream` | 秒级同批 | **强** | `body_full.txt` REQ[2]→REQ[3] |
| `aweme/stats` | `aweme/detail` | 秒级 | **强** | `signature_headers.json` |
| `service/2/app_log` | `comment/list/stream` | 秒级 | **强** | `diag_cmt_caller.txt` |

### 4.3 上报内容

| 上报接口 | 载荷量级 | 事件数 | 可读性 | 关键字段 | 加密归属 |
|---|---|---|---|---|---|
| `service/2/app_log` | 146 KB（实测） | 57 条 | **可读** | 包头 `key`(AES)/`iv` **明文**；`event_v3[].params` **明文 dict**（`enter_from`/`trigger_way`/`doc_type`/`enter_group_id`/`log_id`…） | 无（明文） |
| `search/memory/upload_ei_feature` | ~3.9 KB | - | `[未知]` | 特征向量 | 转 protocol-signature-reverser |
| `aweme/stats` | `[未证]` | - | `[未证]` | - | - |

### 4.4 上报通道

| 通道 | 接口 | 职责 | 是否含指纹 |
|---|---|---|---|
| AppLog | `/service/2/app_log/` + `/performance/p2/` | 批量事件、性能 | `[未证]`（`header` 字段疑含设备参数） |
| 搜索特征 | `/search/memory/upload_ei_feature` | 搜索侧专项特征 | `[未证]` |
| 行为统计 | `/aweme/stats` | 播放行为 | `[未证]` |

---

## 五、★ 本地复刻规格

### 5.1 访问序列（照抄执行顺序）

**搜索链路**
```
step 1: POST i.snssdk.com/aweme/v1/search/history_words_record/
        参数来源: 本地生成              | 依赖: -
step 2: POST aweme.snssdk.com/aweme/v2/search/general/stream/
        参数来源: 本地生成(90 参数)      | 依赖: -           ← 主体
step 3: POST aweme.snssdk.com/aweme/v1/search/memory/upload_ei_feature/
        参数来源: 本地生成              | 依赖: step2（须同批紧随）
step 4: GET  tsearch.toutiaoapi.com/2/wap/search/extra/tts/   （词典卡时）
step 5: POST i.snssdk.com/aweme/v1/search/refresh_related_search/
step 6: POST aweme.snssdk.com/aweme/v1/search/multi_conversation/ai_guide_bar
```

**评论链路**
```
step 1: GET  aweme.snssdk.com/aweme/v1/aweme/detail/?aweme_id=<aid>
        参数来源: 本地生成              | 依赖: -
        产出: sec_uid / comment_count / authentication_token
step 2: UI  触达评论入口（点击 comment_container）
        说明: 评论不自动加载，必须触达 | 依赖: step1
step 3: POST aweme.snssdk.com/aweme/v2/comment/list/stream/
        参数来源: 本地生成 + step1 产出(aweme_author/comment_count)
                  + 服务端签发(authentication_token)
        依赖: step1 + step2
step 4: POST <host>/service/2/app_log/
        参数来源: 本地生成              | 触发时机: step3 完成后立即
```

### 5.2 每笔复刻要点表

| step | 接口 | 关键参数 | 参数来源 | 必须的凭证 | 头/签名要求 | 可否省略 | 省略后果 |
|---|---|---|---|---|---|---|---|
| A1 | `history_words_record` | 历史词 | 本地生成 | - | 全套签名头 | 疑不可省 | `[未证]`（V-1） |
| A2 | `search/general/stream` | keyword/count/cursor/bcm_chain | 本地生成 | - | **全套签名头 + Cookie** | **不可省** | 空壳或 -99999 |
| A3 | `upload_ei_feature` | 特征 | 本地生成 | - | 全套签名头 | 疑不可省 | `[未证]`（V-1） |
| C1 | `aweme/detail` | aweme_id | 本地生成 | - | 全套签名头 | **不可省** | 后续无 `aweme_author`/`comment_count` |
| C3 | `comment/list/stream` | aweme_id/cursor/authentication_token/aweme_author/comment_count | 混合（见 §二） | **authentication_token** | **全套签名头** | **不可省** | **-99999 硬拒绝**（实测） |
| C4 | `app_log` | 埋点事件 | 本地生成 | - | 全套签名头 | 疑不可省 | `[未证]`（V-2） |

**必需请求头清单**（实测抓到，`capture/signature_headers.json`）
```
x-argus                       (八神)
x-gorgon                      (八神)
x-ladon                       (八神)
x-khronos / x-helios / x-medusa
x-ss-stub                     (body 签名)
x-ss-dp
x-tt-token                    长期令牌（跨请求不变）
x-tt-token-supplement
bd-ticket-guard-key-sign
x-tt-dt                       (设备令牌)
x-tt-request-tag
x-vc-bdturing-sdk-version
Cookie: sessionid / sid_guard / odin_tt / d_ticket / multi_sids /
        install_id / passport_mfa_token / passport_assist_user / …
```

### 5.3 节奏与顺序要求

| 项 | 实测值/要求 | 证据 |
|---|---|---|
| 搜索翻页间隔 | 4–5 s（实测 3 页 133 条稳定） | `results_咖啡.json` |
| 评论翻页间隔 | 3 s（8 次滑动 9→16→…→55 条递增） | `comments_7581630849533316401.json` |
| **严格串行的步骤** | 评论链路 C1→C2→C3（有数据依赖）；搜索 A2→A3（同批上报） | §三 |
| 上报窗口 | 上报须落在目标请求的**同一会话窗口**内（秒级） | `body_full.txt` |
| 每页条数 | 搜索 count=10（返回约 68 条卡片）；评论 count=20 | 实测 |

### 5.4 本地实现检查清单

- [ ] **前置接口是否都发了**（搜索 `history_words_record`；评论 `aweme/detail`）
- [ ] **前置产出是否被正确引用**（评论的 `aweme_author` / `comment_count` 取自详情响应）
- [ ] **服务端签发凭证是否回带**（`authentication_token`）
- [ ] **配套上报在目标请求后同批发出**（`upload_ei_feature` / `app_log`）
- [ ] **参数完整性**：90 个搜索参数全带（"只带必要参数"本身即脚本指纹）
- [ ] **头清单与真实 App 一致**（含 native 层注入的八神签名 + 22 条 Cookie）
- [ ] **节奏符合实测间隔**（翻页 3–5 s）
- [ ] **评论链路按 C1→C2→C3 串行**，未跳步

---

## 六、签名与传输（本地复刻的硬门槛）

### 6.1 签名位置（关键）

签名头**由 native 层注入 TLS 流**，Java 层 `RequestBuilder` 的 header 列表为空。

> **教训**：仅 hook Java 层签名方法（`MSManager.frameSign`）会得到 0 命中，
> 从而**错误地**得出"八神不在链路"的结论。权威证据是**传输层实际字节**。

**获取方式**：`hook libsscronet!SSL_write → HTTP/2 帧 → HPACK 索引解码 → HPACK Huffman 解码`
（实现：`scripts/cap_h2_headers.py`）

### 6.2 传输层

| 项 | 实测 |
|---|---|
| 协议 | HTTP/2（`ttnet_h2_enabled:1`）+ **Brotli**（`ttnet_enable_br:1`） |
| Host 调度 | 搜索→`search3-search.amemv.com`；feed→`api3-core-c`；普通→`api3-normal-c` |
| 评论接口 | **未被 TLS 抓包捕获**（疑 QUIC），但 `ChunkDataStream` 稳定取到数据 → 待验证 V-4 |
| 响应加密 | 评论响应为**应用层加密 chunk**（69 字节密文，非 gzip/zlib/br/zstd，未解） |

---

## 七、降级判据（本地自检用）

| 级别 | 特征 | 判据 | 处置 |
|---|---|---|---|
| **OK** | 含业务字段 | 响应含 `aweme_list`/`card_name`/`cid` 等 | 继续 |
| **软降级** | 空壳 | HTTP 200 + `status_code:0` 但 `has_more:0` 且 `category_list:[]`/`comments:[]` | 熔断 + 归因 |
| **硬拒绝** | 风控码 | `status_code:-99999` | 立即停止 |

> **三级均不得仅凭 HTTP 200 或业务 code 判成功**（AGENTS.md 禁词纪律）。
> 判官实现参考：`scripts/risk_health.py::judge_response`

---

## 八、待验证实验清单

| 编号 | 假设 | 实验设计（阻断实验） | 优先级 |
|---|---|---|---|
| **V-1** | 缺前置/上报致降级 | 阻断 `history_words_record` 或 `upload_ei_feature`，观察搜索响应是否变空壳 | **高** |
| **V-2** | 缺 `app_log` 上报致降级 | 阻断该上报，观察评论响应 | **高** |
| **V-3** | `comment_common_comment_data` 是否加密 | 对比多次请求 body 形态 | 中 |
| **V-4** | 评论传输路径（是否 QUIC） | 枚举 BoringSSL 实例 / 抓 UDP | 中 |
| **V-5** | 签名头时效性 | 隔时重放同一签名头，观察是否失效 | 中 |
| **V-6** | 埋点包可读性（搜索特征通道） | 解析 `upload_ei_feature` 载荷 | 低 |

> **纪律**：V-1/V-2 涉及"缺 A 导致 B"的因果断言 —— **在跑完阻断实验前，只能标「推测」**。
> 目前 V-1/V-2 均未做 → 文中相关结论已标 `[未证]`。

---

## 附：本规格的已完成度自检

| 项 | 状态 |
|---|---|
| 三段时序（前/中/后） | ✅ 三条链路全覆盖 |
| 逐笔参数快照 + 来源标注 | ✅ |
| 数据依赖链 | ✅（评论链路强依赖已标注） |
| 前置埋点链路六问 | ✅（4.3/4.4 无证据处标 `[未知]`/`[未证]`） |
| 本地复刻规格（序列+要点表+检查清单） | ✅ |
| 配对关系表 | ✅（§四） |
| 降级判据 | ✅ |
| 待验证清单 | ✅（6 项，因果类已标推测） |
| **可否据此实现本地访问** | **部分** —— 签名头已可从 `signature_headers.json` 复用；评论响应解密未解（V-4 相关） |

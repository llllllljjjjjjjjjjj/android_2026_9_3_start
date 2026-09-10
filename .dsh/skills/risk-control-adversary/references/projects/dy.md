# dy 风控记录

- 状态: 分析中（三条链路已通，风控链路已实证）
- 平台: Android
- 最后更新: 2026-09-10
- 方案文档: projects/dy/docs/risk-control-plan.md
- 目标: 抖音 38.0.0 (380001) / com.ss.android.ugc.aweme
- 设备: Pixel 4 (flame) / Android 10 / SDK 29 / arm64-v8a / Magisk

## 接口风控速查表

| 接口ID | 端点 | 风控维度 | 对抗手段 | 证据等级 | 状态 | 证据 |
|---|---|---|---|---|---|---|
| IF-01 | POST `/aweme/v2/search/general/stream/` | 签名+前置埋点+会话凭证 | RPC 桥接（App 自发生成） | 已实证 | 已破（RPC 路径） | `capture/body_full.txt` |
| IF-02 | POST `/aweme/v1/search/memory/upload_ei_feature/` | **前置特征上报** | 不可绕过（须随业务请求配对） | 已实证 | 识别 | `capture/body_full.txt` REQ[3] |
| IF-03 | POST `/aweme/v1/search/history_words_record/` | 前置行为记录 | 同上 | 已实证 | 识别 | `body_full.txt` REQ[1] |
| IF-04 | GET `/aweme/v1/aweme/detail/` | 签名+播放上报前置 | RPC 桥接 | 已实证 | 已破（RPC 路径） | `capture/signature_headers.json` |
| IF-05 | GET `/aweme/v1/aweme/stats/` | 播放行为上报 | 须随详情请求 | 已实证 | 识别 | 同上 |
| IF-06 | POST `/aweme/v2/comment/list/stream/` | 签名+凭证+QUIC+响应加密 | RPC 桥接（数据层读取） | 已实证 | 已破（RPC 路径）/ 协议直发受阻 | `capture/comment_request_capture.json` |
| IF-07 | POST `/service/2/app_log/` | 批量埋点上报 | 不可绕过 | 已实证 | 识别 | `capture/resp_pottery_47_*.json` |
| IF-08 | POST `/aweme/v1/comment/list/reply/` | 二级回复（带 comment_token） | 未做 | 小样本 | 未动 | `capture/diag_cmt_caller.txt` |
| IF-09 | POST `/aweme/v2/startup/popups/` | 启动弹窗（伴随） | - | 已实证 | 识别 | `signature_headers.json` |

状态取值：已破 / 进行中 / 未动 / 死路。

## 「单接口全链路风控分析」产出（本次新增工作流）

按 SKILL.md 工作流 D 对三条链路逐接口分析，完整产出见 `projects/dy/docs/flow-and-risk.md`。

| 链路 | 前置埋点 | 会话凭证 | 签名 | 传输 | 响应 |
|---|---|---|---|---|---|
| 搜索 | `upload_ei_feature` + `history_words_record` + `bcm_chain` | `search_id`(服务端签发) / `search_session_id` | 八神+ClientKey | H2+Brotli | `dcm` 曝光凭证 + 软降级 |
| 视频 | `aweme/stats` 播放上报 | `authentication_token` | 同上 | H2+Brotli | CDN 时效签名 |
| 评论 | 前置 `aweme/detail` + `app_log` | `authentication_token` + `session_id`(`aid:uid:ts`) | 同上 | 未捕获(疑 QUIC) | 加密 chunk + `-99999` |

## 请求策略实测数据（黄金素材，保留原始数字）

| 日期 | 参数 | 实测值/阈值 | 证据 |
|---|---|---|---|
| 2026-09-10 | 搜索翻页间隔 | 4s（脚本默认），实测 3 页共 133 条稳定 | `capture/results_咖啡.json` |
| 2026-09-10 | 评论翻页间隔 | 3s，8 次滑动 9→16→23→27→33→39→47→55 条递增 | `capture/comments_7581630849533316401.json` |
| 2026-09-10 | 埋点配对率（实测） | search 1/1、comment 3/3、video 1/1（ratio=1.0） | `scripts/risk_health.py` 输出 |
| 2026-09-10 | 无签名头直发 | `status_code: -99999`（硬拒绝） | `capture/comment_direct_response.txt` |
| 2026-09-10 | 带签名头直发 | `-99999` 消失 → 69 字节加密 chunk | 同上 |
| 2026-09-10 | 服务端签发凭证 | `search_id` 格式 `YYYYMMDDHHMMSS`+22hex，每次搜索新签发；`session_id` 跨搜索复用 | `capture/response_full.txt` |

## 公开情报（Web，与本地资料分开，标注可信度）

| 日期 | 主题 | 要点 | 可信度 | 来源 URL |
|---|---|---|---|---|
| - | - | 本次未检索公开情报 | - | - |

## 关键结论

1. **请求前置链路是硬约束**：搜索必发 `history_words_record`→`general/stream`→`upload_ei_feature`（同批复现两轮，顺序固定）；
   评论必先 `aweme/detail` 再 `comment/list/stream`。业务请求与紧邻特征上报构成配对。
2. **签名在 native 层**：八神（`x-argus`/`x-gorgon`/`x-ladon`）+ `x-tt-token` + `bd-ticket-guard-key-sign`
   由 native 直接注入 TLS 流，**Java 层 hook（`MSManager.frameSign`）0 命中** —— 依据 Java 层观测会得出「八神不存在」的错误结论。
3. **降级分级**：软降级（搜索空壳 `{"has_more":0,"category_list":[]}`）vs 硬拒绝（评论 `-99999`）。
   两者都**不可当作成功**（AGENTS.md 禁词纪律）。
4. **会话凭证服务端签发**：`search_id`（每次搜索）/ `authentication_token`（评论、弹幕），客户端不可伪造；
   `dcm` 是曝光回传凭证。
5. **埋点包可读**：`/service/2/app_log/` 的 `key`/`iv` 在包头明文，`event_v3[].params` 实测明文可读。

## 失败模式

| 日期 | 场景 | 失败原因 | 教训 | 关联 F 条目 |
|---|---|---|---|---|
| 2026-09-10 | 无签名头协议直发评论 | 缺 native 层签名头 | 直发前必须先抓齐签名头 | 候选 F-06 |
| 2026-09-10 | Java 层 hook 判「八神不存在」 | 签名在 native 层，Java 层不可见 | 勿以单一层次观测否定机制存在 | 候选 F-06 |
| 2026-09-10 | hook `HashMap.put` | 热路径 + 构造对象 → App SIGSEGV | 禁止 hook 高频集合方法并在内做重操作 | 候选 F-07 |
| 2026-09-10 | frida 单进程加载 2 个脚本 | `script has been destroyed` | 多能力合并为单脚本 | 候选 F-07 |

## 泛化提炼（L3 → L1 沉淀登记，见 general-principles.md §0.4）

| 日期 | 类型 | 编号 | 泛化角度 |
|---|---|---|---|
| 2026-09-10 | 新增 E | E-28 | 请求前置链路配对校验（业务请求与紧邻特征上报构成风控输入） |
| 2026-09-10 | 新增 E | E-29 | 服务端签发会话凭证的串联与回带 |
| 2026-09-10 | 新增 E | E-30 | 降级分级识别（软降级 vs 硬拒绝） |
| 2026-09-10 | 新增 E | E-31 | 风控签名位于 native 层（跨层观测不可互相否定） |
| 2026-09-10 | 新增 E | E-32 | 单接口全链路风控分析（七层链路法） |
| 2026-09-10 | 新增 F | F-06 | 协议直发缺 native 签名头导致硬拒绝 + 跨层误判 |
| 2026-09-10 | 新增 F | F-07 | 高频 hook 点与多脚本加载导致进程崩溃 |

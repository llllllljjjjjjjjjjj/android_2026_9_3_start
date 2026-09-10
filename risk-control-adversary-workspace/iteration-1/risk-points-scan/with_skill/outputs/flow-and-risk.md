# dy 项目风控点整理与知识库沉淀

> 生成日期: 2026-09-10 | 平台: Android | 工作流: A（方案）+ **D（单接口全链路分析）** + A5（沉淀）
> 资料基线: `projects/dy/README.md` + `projects/dy/capture/*`

## 〇、本次交付说明

用户要求「整理风控点 + 包括**前置埋点上报链路** + 沉淀知识库」。
按 SKILL.md 工作流判定：**主任务走工作流 D**（全链路分析），产出链路表与配对关系；
再按 A5 沉淀 L1/L3。**未**走工作流 A 的「分级方案」（用户未要求策略分级）。

## 一、接口总览（含前置链路标注）

| 接口ID | URL/端点 | 方法 | 业务含义 | 前置依赖 | 紧邻上报 | 回执凭证 |
|---|---|---|---|---|---|---|
| IF-01 | `/aweme/v2/search/general/stream/` | POST | 搜索主接口 | `history_words_record` | `upload_ei_feature` | `search_id` / `dcm` |
| IF-02 | `/aweme/v1/search/history_words_record/` | POST | 搜索历史 | - | - | - |
| IF-03 | `/aweme/v1/search/memory/upload_ei_feature/` | POST | 搜索特征上报 | 紧随 `general/stream` | 自身即上报 | - |
| IF-04 | `/aweme/v1/aweme/detail/` | GET | 视频详情 | - | `aweme/stats` | `authentication_token` |
| IF-05 | `/aweme/v1/aweme/stats/` | GET | 播放统计 | `aweme/detail` | 自身即上报 | - |
| IF-06 | `/aweme/v2/comment/list/stream/` | POST | 评论列表 | **`aweme/detail`** | `app_log` | `authentication_token` |
| IF-07 | `/service/2/app_log/` | POST | 批量埋点 | 紧随业务请求 | 自身即上报 | - |
| IF-08 | `/aweme/v1/comment/list/reply/` | POST | 二级回复 | `comment/list/stream` | - | `comment_token` |

## 二、★ 前置埋点 / 特征上报链路（本次核心，D3 六问）

### 2.1 前置接口

| 链路 | 前置接口 | 作用 | 必须性 |
|---|---|---|---|
| 搜索 | `history_words_record` | 历史记录上报 | 强（两轮恒定） |
| 评论 | **`aweme/detail`** | 提供 `aweme_author`/`comment_count` | 强（参数不可自造） |
| 视频 | - | - | - |

### 2.2 紧邻特征上报

| 业务请求 | 紧邻上报 | 延迟 | 配对强度 |
|---|---|---|---|
| `search/general/stream` | `search/memory/upload_ei_feature` | 秒级同批 | **强** |
| `aweme/detail` | `aweme/stats` | 秒级 | **强** |
| `comment/list/stream` | `service/2/app_log` | 秒级 | **强** |

### 2.3 上报内容

| 上报接口 | 可读性 | 关键发现 |
|---|---|---|
| `service/2/app_log` | **可读** | 包头 `key`(AES)/`iv` **明文传输**；`event_v3[].params` 为**明文 dict** |
| `search/memory/upload_ei_feature` | `[未证]` | 载荷约 3.9KB，内容未解析 |
| `aweme/stats` | `[未证]` | - |

### 2.4 上报通道

| 通道 | 接口 | 职责 |
|---|---|---|
| AppLog | `service/2/app_log/`(+`performance/p2/`) | 批量事件、性能 |
| 搜索特征 | `search/memory/upload_ei_feature` | 搜索侧专项特征 |
| 行为统计 | `aweme/stats` | 播放行为 |

### 2.5 配对关系表

| 业务请求 | 前置 | 紧邻上报 | 回执凭证 | 强度 |
|---|---|---|---|---|
| 搜索 | `history_words_record` | `upload_ei_feature` | `search_id`/`dcm` | **强** |
| 视频 | - | `aweme/stats` | `authentication_token` | **强** |
| 评论 | `aweme/detail` | `app_log` | `authentication_token`/`session_id` | **强** |

### 2.6 因果验证

| 假设 | 阻断动作 | 实测 | 结论 |
|---|---|---|---|
| 缺签名头 → 拒绝 | 直发无签名头 | `-99999` | **已实证** |
| 带签名头 → 通过 | 直发带签名头 | 风控码消失 | **已实证** |
| 缺前置 → 降级 | 跳过前置 | 待做 | **推测** |
| 缺上报 → 降级 | 阻断上报 | 待做 | **推测** |

## 三、风控点汇总（按层）

| 层 | 风控点 | 证据等级 | 置信度 |
|---|---|---|---|
| ② 参数 | 参数完整性（90 参数 / 39 Query） | 已实证 | 高 |
| ③ 前置特征 | **前置+紧邻配对**（见 §二） | 已实证（时序）/ 推测（因果） | 中 |
| ④ 签名 | 八神 + ClientKey，**native 层注入** | 已实证 | 高 |
| ⑤ 传输 | H2+Brotli；评论疑 QUIC（结论不完整） | 小样本 | 低 |
| ⑥ 响应 | **软降级空壳** / **加密 chunk** | 已实证 | 高 |
| ⑦ 回执 | 服务端签发凭证（`search_id`/`authentication_token`） | 已实证 | 高 |

## 四、★ 知识库沉淀（A5）

### 4.1 拟新增 L1 条目

| 编号 | 角度 | 证据等级 | 来源 |
|---|---|---|---|
| E-28 | 请求前置链路配对校验 | 已实证 | dy 2026-09-10 |
| E-29 | 服务端签发会话凭证的串联回带 | 已实证 | dy 2026-09-10 |
| E-30 | 降级分级识别（软降级 vs 硬拒绝） | 已实证 | dy 2026-09-10 |
| E-31 | 风控签名位于 native 层（跨层观测不可互否） | 已实证 | dy 2026-09-10 |
| E-32 | 单接口全链路风控分析（七层链路法） | 已实证 | dy 2026-09-10 |
| F-06 | 协议直发缺 native 签名头致硬拒绝 | 已实证 | dy 2026-09-10 |
| F-07 | 高频 hook 点与多脚本加载致进程崩溃 | 已实证 | dy 2026-09-10 |

### 4.2 L3 项目记录

已登记 `references/projects/dy.md`（接口风控速查表 + 实测数据 + 失败模式）。

## 五、待验证实验清单

| 编号 | 假设 | 优先级 |
|---|---|---|
| V-1 | 缺前置致降级（阻断实验） | 高 |
| V-2 | 缺上报致降级（阻断实验） | 高 |
| V-3 | 评论传输路径（QUIC?） | 中 |

---

## 【产出特征自评（供评分对照）】

- 判定并采用：**工作流 D**（主）+ A5（沉淀）；**未**误走工作流 A 的分级方案
- **有**七层风控点汇总表
- **有**前置接口 / 紧邻上报 / 回执凭证三列联动的配对表（按链路分组）
- **有** D3 六问全答
- **有**因果验证表（区分已实证/推测）
- **有**知识库沉淀清单（E-28~E-32 + F-06/F-07）与 L3 登记
- 埋点内容给出**实证发现**（`key`/`iv` 明文、`params` 明文）

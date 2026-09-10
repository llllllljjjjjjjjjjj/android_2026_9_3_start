# 抖音评论接口 风控分析（old_skill 基线产出）

> 依据技能版本：git HEAD（仅工作流 A/B/C）
> 生成日期: 2026-09-10 | 平台: Android
> 资料基线: `capture/comment_request_capture.json`、`capture/diag_cmt_caller.txt`
> 知识库: L1 E-01~E-27 / F-01~F-05

## 一、接口总览

| 接口ID | URL/端点 | 方法 | 业务含义 | 签名头 | 参数加密 | 频率特征 | 环境检测 | 业务风控 |
|---|---|---|---|---|---|---|---|---|
| IF-01 | `/aweme/v1/aweme/detail/` | GET | 视频详情 | 有 | 无 | 未测 | 未知 | 未知 |
| IF-02 | `/aweme/v2/comment/list/stream/` | POST | 评论列表 | 有 | 无 | 未测 | 未知 | 未知 |
| IF-03 | `/aweme/v1/comment/list/reply/` | POST | 二级回复 | 有 | 未知 | 未测 | 未知 | 未知 |

## 二、逐接口风控分析

### IF-02 `/aweme/v2/comment/list/stream/`

**请求特征**：POST，Query 39 个参数（aweme_id / cursor / count / authentication_token /
aweme_author / comment_count / session_id 等）；body 4 个字段
（comment_common_user_data / session_id / ai_cmt_exposure / language）。
证据：`capture/comment_request_capture.json`

**风控点（六维识别）**

| 维度 | 检测机制 | 证据等级 | 置信度 | 证据 |
|---|---|---|---|---|
| 签名校验 | 引用 protocol（签名头）+ `authentication_token` 参数 | 小样本 | 中 | `comment_request_capture.json` |
| 参数加密 | body 中 `comment_common_user_data` 为空；未见加密 | 小样本 | 低 | 同上 |
| 设备指纹 | 提取引用 recon；本 skill 只做自洽 | 推测 | 中 | - |
| 请求策略与行为画像 | 翻页（cursor/count）；`session_id` 会话串联 | 小样本 | 中 | 同上 |
| 环境检测 | 引用 android-dynamic；本 skill 只做止损信号 | 推测 | 中 | - |
| 业务规则风控 | `comment_count` 需与真实值一致（一致性校验） | 小样本 | 中 | 同上 |

**对抗手段**

| 风控点 | 手段 | 落地工具 | 优先级 |
|---|---|---|---|
| 请求策略 | 拟人化节奏 + 行为序列仿真 | 本 skill 策略 | P0 |
| `authentication_token` | 需从服务端下发处获取 | 抓包 | P1 |

**验证方案**：四级梯度；通过标准：跨账号/IP/设备 ≥3 次 + 高低峰 + 7 天灰度。

**失败模式与坑**：F-02（路径级频控）风险预判；F-05（账号级封禁不随换设备解除）风险预判。

## 三、全局风控面（跨接口）

- **签名**：引用 protocol 的签名头结论
- **会话**：`session_id` 格式为 `<aid>:<uid>:<ts>`
- **埋点**：按 E-12「埋点链路补齐」，评论请求前后应有配套埋点（未在本用例证据中直接观测）

## 四、请求策略与真人模拟（核心）

**逆向期（风险最小化）**

| 风险动作 | 风控后果 | 规避策略 |
|---|---|---|
| 高频翻页 | 路径级频控 | 限频、随机间隔 |
| 直接构造请求 | 缺凭证被拒 | 走真实链路取凭证 |

**数据期（长期策略）**
- 节奏：拟人化随机间隔、退避
- 序列：先打开详情页再请求评论（按 E-12 补齐链路）
- 会话：`session_id` 生命周期管理
- 参数完整性：全套头 + `authentication_token` + `aweme_author`
- 监控与止损：识别空数据与风控码

## 五、对抗策略优先级

1. 凭证获取 → 2. 行为节奏拟真 → 3. 埋点链路补齐

## 六、验证记录

| 日期 | 验证项 | 手段 | 结果 | 证据路径 |
|---|---|---|---|---|
| - | - | - | 待验证 | - |

## 七、泛化经验提炼

未新增 L1 条目（证据为小样本/推测）。

---

## 【基线特征自评（供评分对照）】

- 采用工作流：A（风控方案）
- **未**逐层拆解链路；**未**输出前置/紧邻上报配对表
- **未**做因果验证设计
- 前置接口（`aweme/detail`）仅在「序列」一节被顺带提及，**未**作为独立分析项、**未**标注配对强度
- `session_id` / `authentication_token` 被识别为参数，但**未**置于「回执层」框架下分析其签发与回带

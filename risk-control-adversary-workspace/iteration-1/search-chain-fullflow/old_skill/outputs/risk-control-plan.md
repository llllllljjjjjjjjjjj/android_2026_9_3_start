# 抖音搜索接口 风控分析（old_skill 基线产出）

> 依据技能版本：git HEAD（仅工作流 A/B/C，无「单接口全链路分析」工作流）
> 生成日期: 2026-09-10 | 平台: Android | 资料基线: projects/dy/capture/*
> 知识库: L1 E-01~E-27 / F-01~F-05

## 一、接口总览

| 接口ID | URL/端点 | 方法 | 业务含义 | 签名头 | 参数加密 | 频率特征 | 环境检测 | 业务风控 |
|---|---|---|---|---|---|---|---|---|
| IF-01 | `/aweme/v2/search/general/stream/` | POST | 搜索主接口 | 有（TTNet 注入） | 无 | 未测 | 未知 | 未知 |
| IF-02 | `/aweme/v1/search/history_words_record/` | POST | 搜索历史记录 | 有 | 未知 | 未测 | 未知 | 未知 |
| IF-03 | `/aweme/v1/search/memory/upload_ei_feature/` | POST | 特征上报 | 有 | 未知 | 未测 | 未知 | 未知 |
| IF-04 | `/api/suggest_words/` | GET | 搜索建议 | 有 | 无 | 未测 | 未知 | 未知 |
| IF-05 | `/aweme/v1/search/refresh_related_search/` | POST | 相关搜索 | 有 | 未知 | 未测 | 未知 | 未知 |

> 注：接口来源为 `capture/body_full.txt` 的请求序列；未做的维度标「未知」。

## 二、逐接口风控分析

### IF-01 `/aweme/v2/search/general/stream/`

**请求特征**：POST，form-urlencoded，body 约 90 个参数（keyword / count / cursor / search_session_id /
bcm_chain / template_extra_info / realtime_feature_channel / previous_search_ts 等）。
证据：`capture/body_full.txt`

**风控点（六维识别）**

| 维度 | 检测机制 | 证据等级 | 置信度 | 证据 |
|---|---|---|---|---|
| 签名校验 | 引用 protocol（签名头由 TTNet 层注入，Java 层不可见） | 小样本 | 中 | `capture/signature_headers.json` |
| 参数加密 | 未发现 body 加密（明文 form） | 小样本 | 中 | `capture/body_full.txt` |
| 设备指纹 | 提取引用 recon；本 skill 只做自洽 | 推测 | 中 | - |
| 请求策略与行为画像 | 翻页频控、行为序列；`bcm_chain` 疑似行为链 | 推测 | 中 | 无实测，待对拍 |
| 环境检测 | 引用 android-dynamic；本 skill 只做止损信号 | 推测 | 中 | - |
| 业务规则风控 | 会话串联（`search_session_id`） | 小样本 | 中 | `capture/body_full.txt` |

**对抗手段**

| 风控点 | 手段 | 落地工具 | 优先级 |
|---|---|---|---|
| 请求策略 | 拟人化节奏 + 行为序列仿真 | 本 skill 策略 + 采集脚本 | P0 |
| 签名 | RPC oracle 在线签名 | frida-orchestrator-mcp frida_rpc_call | P1 |

**验证方案**：实验室 → 小流量 → 中流量 → 全量四级梯度；通过标准：跨账号/IP/设备 ≥3 次、
覆盖高低峰、7 天灰度、对照组 A/B 通过率。

**失败模式与坑**：F-02（路径级频控封禁不随设备/IP 更换自动解除）风险预判。

## 三、全局风控面（跨接口）

- **签名**：搜索接口签名头由 TTNet 层注入；`capture/signature_headers.json` 含 `x-argus`/`x-gorgon`/
  `x-ladon`/`x-tt-token` 等（小样本证据）
- **会话**：`search_session_id` 在 body 中传递，属会话维度
- **埋点**：`upload_ei_feature` 属特征上报接口，按 E-12「埋点链路补齐」列为需补齐的链路

## 四、请求策略与真人模拟（核心）

**逆向期（风险最小化）**

| 风险动作 | 风控后果 | 规避策略 |
|---|---|---|
| oracle 高频调用 | 设备级限流/拉黑 | 限频、错峰 |
| hook 注入时机不当 | 触发环境检测 | 错开冷启动窗口 |

**数据期（长期策略）**
- 节奏：拟人化随机间隔、作息时段、批量大小、退避
- 序列：预热/配套接口在目标请求前后调用（按 E-12 补齐埋点链路）
- 会话：登录态生命周期、账号-设备绑定
- 参数完整性：全套头清单，可选参数不省略
- 频率预算：单设备每日预算与增速节奏
- 监控与止损：封禁信号识别、自动熔断

## 五、对抗策略优先级

1. 签名获取（P1）→ 2. 行为节奏拟真（P0）→ 3. 埋点链路补齐（P1）

## 六、验证记录

| 日期 | 验证项 | 手段 | 结果 | 证据路径 |
|---|---|---|---|---|
| - | - | - | 待验证 | - |

## 七、泛化经验提炼

本次未新增 L1 条目（证据多为小样本/推测，未达准入）。

---

## 【基线特征自评（供评分对照）】

- 采用工作流：A（生成风控方案）—— 产出 `risk-control-plan.md` 结构
- **未**逐层拆解链路（无七层结构）
- **未**输出"前置接口 / 紧邻上报"配对表
- **未**做因果验证实验设计（仅列「待验证」）
- 埋点仅作为 E-12 的一条引用提及，**未**系统梳理前置链路

---
name: reverse-kit-index
description: Android 逆向便携工作台「技能总索引」，由原 7 份 SKILL.md 转化生成。当任务涉及逆向、或不确定该用哪个技能、或需要了解全部技能分工时加载本技能做路由；每个技能的作用直接引用其原 SKILL.md 的 description。触发词：技能总览、skill清单、技能索引、技能路由、该用哪个技能、所有技能、7个技能、哪个skill、分工。
whenToUse: 用户询问技能清单/分工、任务较模糊需要路由到专项技能、或需要了解整个逆向工作台能力时
---
# Reverse Kit — 技能总索引

> 本技能是路由/索引：**不执行具体逆向**，负责把任务分派到 7 个专项技能。
> 每行「作用」**直接引用原 SKILL.md 的 description**（原样转化），触发词包含在其中。
> 确认目标后，用 skill 工具加载对应技能。

## 技能总览（来自原 SKILL.md frontmatter）

| 技能 | 作用（原 SKILL.md description） | 边界 |
|------|----------------------------------|------|
| **android-recon** | Android 逆向「侦察与静态分析」总入口。负责拿到 APK 后的第一阶段：设备连接（真机优先 Pixel 4 / MuMu fallback）、证书持久化、jadx/apktool 反编译、API/调用链提取（接 reverse_index 索引）、抓包治理（代理端口校准/SSL Pinning 初判/r0capture/proxy 残留断网排查/QUIC 抓包）、APK malformation 修复，并把任务路由到脱壳/动态/签名三个专项 skill。触发词：APK反编译、提取API、调用链追踪、jadx、apktool、连真机、连模拟器、MuMu、证书持久化、抓包、抓不到包、真机没网、代理残留、QUIC、malformation、Android逆向入口。 | 不做脱壳/Hook/签名还原 |
| **android-unpack** | Android 脱壳与加固破解专项。负责「壳识别 → 策略选择 → 脱壳执行 → DEX/SO 验证」。支持 360/腾讯/百度/梆梆/爱加密/网易易盾等商业加固；提供 Frida 动态脱壳、Root 内存提取、抽取壳 frida 主动调用 dumper、内存快照、反调试绕过、VDEX 提取、以及运行期解密壳的 native SO 代码段脱密（梆梆/爱加密）。触发词：脱壳、加固破解、DEX提取、SO脱密、壳识别、VDEX、爱加密、梆梆、360加固、腾讯加固、网易易盾、Root内存提取、抽取壳、FART、Youpk、BlackDex、主动调用。 | 脱完交 android-recon 做静态分析 |
| **android-dynamic** | Android 动态调试专项。负责运行期 Frida Hook、Frida 版本兼容、反 Frida 三层检测对抗（Zygisk 默认注入向量 / maps 抹除 / root 内存 dump 零注入逃生门）、spawn-vs-attach、商业加固 hook 层规则（quicksparrow/ANet）、Root 检测绕过、SSL Pinning 8 方案选择器、SO 分析（IDA/Stalker/Unicorn 快照/RDTSC/D-810 CFF）、注册级完整性检测清单。内含 APP 安全等级矩阵与「及时止损线」。触发词：Frida、Hook、动态调试、frida检测、反检测、注入秒退、attach崩server、ZygiskFrida、spawn注入、SSL pinning、抓包绕过、SO分析、Stalker、Unicorn、RDTSC、D-810、CFF、native hook、quicksparrow、objection、Florida、ecapture、完整性检测。 | 不做纯算实现/签名还原（交 protocol-signature-reverser） |
| **protocol-signature-reverser** | 协议签名逆向专家。专门逆向APP的API签名算法（HTTP Header签名、URL参数签名、Body签名）。6路并行分析框架（SO静态/动态抓包/Frida Hook/Unicorn模拟/文献/开源参考）+ 算法还原策略选择器 + 生命周期绑定/混合加密/unidbg执行正确性止损。触发词：签名逆向、sign破解、x-mini、x-sign、shield、协议破解、算法还原、signature reverse、加密参数逆向、ct_client、e9hgat5k、loginAuthCipher、凯撒、滑块、CKey、MTOP、生命周期绑定、在线兜底、unidbg、混合加密、RSA随机填充。 | 不做运行期 Hook（交 android-dynamic） |
| **reverse-skill-evolver** | 逆向技能自进化系统。基于达尔文.skill的棘轮机制，每次完成逆向任务后自动评估→改进→测试→保留或回滚。9维逆向领域评分体系（工具有效性/策略覆盖/失败编码/决策树/黑名单/SO策略/抓包/Frida矩阵/实测）。触发词：进化逆向技能、更新策略矩阵、记录失败模式、评估逆向 skill、优化技能、技能进化。 | 元技能，管理前 4 个逆向技能 |
| **darwin-skill** | Darwin Skill 2.0 (达尔文.skill 2.0): autonomous skill optimizer, v2.0 integrates Microsoft Research SkillLens (arXiv 2605.23899) 9-dim rubric + SkillOpt (arXiv 2605.23904) validation-gated design + human-in-the-loop checkpoints. Evaluates SKILL.md files using a 9-dimension rubric (structure + effectiveness + meta-skill blacklists), runs hill-climbing with git version control, spawns independent judge agents for blind evaluation, validates improvements through test prompts with auto-break on diminishing returns, and generates visual result cards. Use when user mentions "优化skill", "skill评分", "自动优化", "auto optimize", "skill质量检查", "达尔文", "darwin", "帮我改改skill", "skill怎么样", "提升skill质量", "skill review", "skill打分". | 通用 skill 优化框架，不限于逆向 |
| **risk-control-adversary** | 风控对抗方案设计师。分析 projects/ 下逆向项目的资料（静态文档/抓包/Hook记录），识别每个接口的风控点（签名校验/参数加密/设备指纹/请求策略与行为画像/环境检测），核心产出是**请求策略与真人模拟方案**——逆向过程中如何最小化触发风控、逆向完成后如何像真人一样稳定拿数据，按统一模板生成《风控对抗方案》写入 projects/<target>/docs/，并把项目风控记录与泛化经验沉淀到本 skill 知识库持续进化。用户提到风控、风控对抗、风控方案、风控点、风控分析、对抗风控、请求策略、真人模拟、模拟请求、频率控制、学习风控经验、风控指导文档、沉淀风控角度、risk control 时都应使用本 skill，即使没有明确说"生成方案"。 | 只读 projects/；只写 docs/risk-control-plan.md |

## 工作流阶段映射

```
§1 环境就绪 / §2 静态分析 / §3 抓包治理  → android-recon（+ reverse_index / frida_orchestrator）
有壳？（jadx 空壳/方法体 nop）            → android-unpack（脱完回 §2）
§4 签名逆向                              → protocol-signature-reverser（+ algo_lab / frida_rpc_call）
§5 动态调试                              → android-dynamic（+ frida_orchestrator / .venv-frida-*）
风控方案                                → risk-control-adversary
技能进化/评估/优化                       → reverse-skill-evolver / darwin-skill
```

## 配套能力速查

| 能力 | 入口 |
|------|------|
| 反编译产物索引/检索 | `mcp__reverse_index__*`（index_project/search_code/find_endpoint/find_symbol…） |
| ADB/Root/Frida 编排、frida_rpc_call、UI 自动化 | `mcp__frida_orchestrator__*`（80 工具） |
| 编码识别、Hash/HMAC 验证、python 复现器 | `mcp__algo_lab__*` |
| Charles 抓包会话 | `mcp__charles__*`（需 GUI 开 8888） |
| jadx / apktool / bundled adb | `tools\jadx\bin\jadx.bat`、`tools\apktool\apktool.bat`、`android_mcp\toolchain\bin\windows\platform-tools\adb.exe` |
| Frida 客户端（版本对齐） | `.venv-frida-16.5.7\`（florida-server/f1657）、`.venv-frida-16.7.19\`（frida-server） |

## 使用方式

1. 按上表匹配任务 → 加载对应技能（skill 工具调用技能名）。
2. 拿不准等级/策略 → 各技能内有判定矩阵（如 android-dynamic 安全等级 L0-L5、android-unpack 加固成功率表）。
3. 任务完成后 → 如需沉淀，交给 reverse-skill-evolver 评估归档。

> 总览与项目根 `AGENTS.md` 一致；各技能细节以 `.dsh/skills/<name>/SKILL.md` 为准。

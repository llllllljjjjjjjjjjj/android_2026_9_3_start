---
name: reverse-skill-evolver
description: 逆向技能自进化系统。基于达尔文.skill的棘轮机制，每次完成逆向任务后自动评估→改进→测试→保留或回滚。9维逆向领域评分体系（工具有效性/策略覆盖/失败编码/决策树/黑名单/SO策略/抓包/Frida矩阵/实测）。触发词：进化逆向技能、更新策略矩阵、记录失败模式、评估逆向 skill、优化技能、技能进化。
whenToUse: 用户要求评估/优化/进化逆向 skills、记录失败模式、更新策略矩阵时
---

# Reverse Skill Evolver — 逆向技能自进化系统

## 角色定位

你是逆向技能的"训练师"。本技能确保 4 个逆向 skill（**android-recon / android-unpack / android-dynamic / protocol-signature-reverser**，必要时含本元技能）随着每个新项目持续进化，只保留有可衡量改进的修改。

> 📌 旧版写 `android-reverse-expert`（已拆成 recon/unpack/dynamic 三个）；本文件已对齐当前 4-skill 结构（2026-06-17 Round 1）。

**设计灵感**：达尔文.skill v2.0（alchaincyf/darwin-skill）+ 微软研究院 SkillLens/SkillOpt 论文。

```
每次逆向任务完成
       │
       ▼
 基线评估 (9维评分)
       │
       ▼
 差距分析 (找最低维度)
       │
       ▼
 针对性改进 (一轮只改一个维度)
       │
       ▼
 独立验证 (子agent重新评分)
       │
   ┌───┴───┐
   │ 分涨了? │
   └───┬───┘
   是 / \ 否
 保留   回滚
```

---

## 核心原则

| # | 原则 | 说明 |
|---|------|------|
| 01 | **单一可编辑资产** | 每次只改一个 SKILL.md，变量可控 |
| 02 | **双重评估** | 结构评分（静态分析）+ 实测（跑一个逆向任务） |
| 03 | **棘轮机制** | 分数只升不降，退步自动回滚 |
| 04 | **独立评分** | 评分用独立子 agent（SkillLens 实证 LLM 自评准确率仅 46.4%） |
| 05 | **人在回路** | 每个 Skill 优化完后暂停，用户确认 |

> 🔴 **源真相（改任何 skill 前必读）**
> - 编辑 **`.dsh/skills/<skill>/SKILL.md`**（唯一源真相，DSH 实时执行源）。
> - DSH 单工具，无需镜像同步；改完即生效。
> - ⚠️ 保持 UTF-8 无 BOM 编码，避免中文损坏。

---

## 9 维逆向领域评估体系（100分制）

> 每维度的详细评分标准见 **[references/evolution-playbook.md](references/evolution-playbook.md)**。

- **结构维度（60 分）**：① 工具路径有效性 /10 ② APP策略矩阵覆盖度 /15 ③ 失败模式编码完整性 /15 ④ 决策树可执行性 /10 ⑤ 工具黑名单时效性 /10
- **效果维度（40 分）**：⑥ SO分析策略准确度 /10 ⑦ 抓包方案成功率 /10 ⑧ Frida版本兼容矩阵 /10 ⑨ 实测验证通过率 /10

---

## 进化循环：5 个 Phase（主干）

> 每个 Phase 的完整执行伪代码、评估报告模板见 **[references/evolution-playbook.md](references/evolution-playbook.md)**。

- **Phase 1 基线评估**：独立子 agent 做 9 维评分 → 输出每维度得分+总分+最低维度。🔴 CHECKPOINT：展示报告，暂停等用户确认改进方向。
- **Phase 2 单维度优化**：一轮只改最低一个维度（单轮涨幅 <1 分自动早停）→ 编辑 SKILL.md + commit → **2 个独立子 agent** 复评 → 新分>旧分保留，否则 `git revert`。🔴 CHECKPOINT：展示 diff+分数变化等确认。
- **Phase 3 回归测试**：随机抽 2 个已完成项目关键步骤用新 skill 重跑，🛑 回归即强制回滚。
- **Phase 4 跨 Skill 联动检查**：4 个逆向 skill 的 ADB/Frida/真机基线统一、cross-ref 有效；失败模式/壳/网络栈/签名案例互相对齐。
- **Phase 5 知识蒸馏归档**：失败模式编码入项目记忆、新 APP 入安全等级矩阵、新签名案例入案例速查、更新 MEMORY.md、记 EVOLUTION_LOG.md、输出进化摘要。

---

## 触发决策路由

```
用户请求
    ├─ "评估逆向 skills"            → Phase 1 → 9维评分 → 暂停确认
    ├─ "优化 <recon|unpack|dynamic|signature>" → Phase 1 → Phase 2 → Phase 3
    ├─ "更新策略矩阵"/"添加新APP"   → Phase 2 直接编辑（skip 基线）
    ├─ "记录失败模式"/"又踩一个坑"  → Phase 5 追加失败模式编码 + 更新项目记忆
    ├─ "全量进化"/"优化所有逆向 skills" → recon→unpack→dynamic→signature→联动→归档（最弱先修）
    └─ "回滚上次进化"              → git log --oneline -5 → 确认目标 → git revert
```

> 反例黑名单 8 条（又改又评/reset --hard 回滚/凑分堆冗余/跳过回归/一轮改多维/干跑>30%/静默异常/忽视相关簇）详见 evolution-playbook.md，**每轮 Phase 2 改动前对照一次，命中即重写方案**。

---

## 进化历史追踪

进化记录在 `.dsh/skills/reverse-skill-evolver/EVOLUTION_LOG.md`（已建）。**Round 1（2026-06-17 全量进化 + 全 memory 蒸馏）**：

| skill | 前 | 后 | 决策 |
|---|:--:|:--:|:--:|
| android-recon | 49 | 78 | KEEP |
| android-unpack | 60 | 80 | KEEP |
| android-dynamic | 73 | 90 | KEEP |
| protocol-signature-reverser | 76 | 88 | KEEP |

> 4/4 KEEP，独立复评零回归/零捏造。后续每轮按同表追加到 EVOLUTION_LOG.md。
>
> **Round 2（2026-08-18）**：记忆蒸馏 + MCP TIMEOUT 对齐。自评 recon 78→86 / unpack 80→84 / dynamic 90→93 / sig 88→94。详见 EVOLUTION_LOG。

---

## 进化触发事件清单

以下事件应触发进化检查：

- [ ] 完成一个新 APP 的逆向分析
- [ ] 发现新的安全检测机制（如新的反 Frida 技术）
- [ ] 工具版本升级导致旧策略失效
- [ ] 用户反馈"按 skill 做失败了"
- [ ] 新的逆向方法论（如新论文/工具发布）
- [ ] 项目记忆达到 40 条（触发全量重审）
- [ ] 每月定期评估（日历提醒）

---

# 参考资料（references/，按需加载）

| 文件 | 内容 | 何时读 |
|------|------|--------|
| [references/evolution-playbook.md](references/evolution-playbook.md) | 9 维评分标准细则、5 Phase 完整伪代码、触发路由、反例黑名单 8 条、评估报告模板、与女娲/达尔文继承关系、快速命令 | 正式跑评估/优化、写报告、对照反例时 |
| EVOLUTION_LOG.md（skill 根目录） | 各轮进化的前分/后分/决策流水 | 查看/追加进化历史 |

# 逆向 Skills 进化日志（Reverse Skill Evolution Log）

> 方法论：darwin 棘轮（9 维独立评分，author≠scorer，只保留涨分，回归即回滚）。详见 `reverse-skill-evolver`。

## Round 1 — 2026-06-17 — 全量进化 + 全 memory 蒸馏

**触发**：用户「skills 都是旧版需要迭代」+「梳理记忆，做过的逆向都可复用、可蒸馏」。
**范围**：`.claude/skills`（Claude Code 实时源）4 个逆向 skill；全 memory 50+ 条按目标聚类蒸馏（XHS / ct_client / 连信 / Bilibili / Apple(SAP/anisette/unicorn/D-810) / Ele.me / 淘宝闪购 MTOP / 设备&env）。
**用户决策**：① 全文自包含（算法/recipe/配置写进 skill）② 编辑 `.claude` → 镜像 `.agents`（不收口 junction）。

| skill | 前分 | 后分 | Δ | 决策 | 主要改动 |
|---|:--:|:--:|:--:|:--:|---|
| android-recon | 49 | **78** | +29 | KEEP | MuMu→Pixel6/bundled-adb 全替换；proxy 残留断网坑(§3.2)；mitmproxy透明+iptables/QUIC libxquic 抓包；reverse-index-mcp index_project 路由；Frida 双 server 矩阵；工具黑名单段 |
| android-unpack | 60 | **80** | +20 | KEEP | 策略D 抽取壳 frida 主动调用 dumper（被动 vs 主动）；§4 SO 代码段脱密（梆梆 rwxp / 爱加密匿名 r-xp + SHIFT 坑 + dd 32-bit 溢出坑 + IDA 段权限修复）；lianxin/ct_client 实战案例；魔改 frida 实名集成 |
| android-dynamic | 73 | **90** | +17 | KEEP | Zygisk 提为**默认注入向量**（配置自包含）；maps 抹除取代 100ms 竞速；root 内存 dump 零注入逃生门 + anti-RASP 阶梯；spawn-not-attach 硬规则 + attach 崩 server；quicksparrow 仅 native；§5 Unicorn 快照/RDTSC/D-810/send-dump/opaque-token；§6 注册级 6 层完整性清单 |
| protocol-signature-reverser | 76 | **88** | +12 | KEEP | 案例速查 4→7（ct_client 族/连信梆梆/淘宝 MTOP）；SF-013 生命周期绑定 / SF-014 unidbg 执行坏 / SF-015 三路全断；策略 RSA（随机填充）+ 策略 G（在线兜底）；ANet/QUIC 抓样本；unidbg sdk23-libc/JNI-SVC 蹦床/靶向堆恢复 |

**独立复评**：4/4 KEEP，零回归（强存量章节计数与备份一致），零捏造（新案例算法形态与 memory ground-truth 字节级对账：loginAuthCipher/e9hgat5k/连信 CKey/MTOP 全吻合），跨 skill 引用一致，关键路径磁盘核验存在（bundled adb 5.8MB、new-server 56MB）。
**镜像**：`.claude` → `.agents`（字符串 `.claude/skills`→`.agents/skills` 重写，UTF-8 **无 BOM**；⚠️ 用 .NET `ReadAllText` 不要 `Get-Content -Raw`，后者按 cp936 误读 UTF-8 中文会损坏）。
**备份**：`.claude/skills/.evolution_bak/`（验证满意后可删）。

### 待办（本轮未做，留下轮）
- `reverse-skill-evolver` 自身 rubric/路由仍写旧技能名 `android-reverse-expert`（早已拆成 recon/unpack/dynamic）→ 需更新。
- 多副本根治：`.claude`/`.agents`/`.codex`/`.qoder` 仍多份物理副本 → 可选 junction 收口（本轮用户选 mirror，未收口）。

---

## Round 2 — 2026-08-18 — 记忆蒸馏 + MCP 对齐（全量进化 Phase 5）

**触发**：用户「检索 Claude/ZCode 记忆和项目经验，对 `.claude` 权威源 skills + MCP 更新迭代」。
**范围**：Round 1 之后 ~2 个月实战（fp_stack、盒马/猫眼、瑞幸、抖音八神、Keeta、Play DG、360VIP、平安、机场/A14 CA、Frida ABI）。
**性质**：知识蒸馏 + 矩阵/失败模式/MCP 契约对齐，不是单维度 hill-climb。独立子 agent 复评未跑（人审后可补）。

| skill | 前分 | 后分(自评) | Δ | 决策 | 主要改动 |
|---|:--:|:--:|:--:|:--:|---|
| android-recon | 78 | **86** | +8 | KEEP | A14 APEX CA；机场上游 7892；网络栈+NAL/TTNet/NV；§3.6 fp_stack；黑名单 Git Bash/17.x |
| android-unpack | 80 | **84** | +4 | KEEP | 360 VIP magic 无关扫描；luckin/pingan 案例；pkill 自杀坑 |
| android-dynamic | 90 | **93** | +3 | KEEP | 矩阵 L3b/L4m/L4d；ABI 禁交叉；美团 attach-pid；D-810 无 UI；算法助手 chown |
| protocol-signature-reverser | 88 | **94** | +6 | KEEP | SF-016~019；策略 H；瑞幸/八神/mtgsig/盒马/Play 案例；MCP 改自建三件套 |
| reverse-skill-evolver | — | — | — | KEEP | SF 计数 19；Phase 5 补 MCP 对齐 |

**MCP**：根 `.mcp.json` 补 `ANDROID_MCP_TOOL_TIMEOUT=90`（原仅 Cursor 有）；`.codex/config.toml` 同步；ZCode/Qoder 用户目录同补。CLAUDE.md 写清 4 工具配置真源 + `.claude.json` 大小写键坑。
**镜像**：`python .claude/scripts/sync_shared_skills.py agents qoder zcode`
**未做**：独立 9 维复评；Codex 用户目录 `~/.codex/config.toml` 仍只有 zai（项目 `.codex/config.toml` 已对齐）；junction 收口仍未做。

### Round 2.1 — 2026-08-18 — MCP 属主漏修 + 全工具同步核验

**代码**：`root_push_file` 首写先 walk 缺失目录、从最近已存在祖先继承属主并对新建目录 `chown`（修 HMA / 嵌套 app 私有路径）；junge package 拒 `../`；回归 `test_root_push_owner_fallback.py` + `test_algorithm_aide_owner.py`。
**同步核验**：五 skill 的 SKILL.md 已对齐（unpack 哈希差仅 `.claude\skills`→`.{target}\skills` 路径替换）。`EVOLUTION_LOG.md` 此前只在 `.claude`/`.cursor`，现由 `sync_shared_skills.py` 一并镜像到 agents/zcode/qoder（codex 为 agents junction）。MCP `ANDROID_MCP_TOOL_TIMEOUT=90` 已在 `.mcp.json` / `.cursor/mcp.json` / 项目 `.codex/config.toml` / `~/.zcode/cli/config.json` / `~/.qoder/mcp.json`；`~/.cursor/mcp.json` 为空（正确）；用户 `~/.codex/config.toml` 仍只有 zai（项目级已对齐，不写入用户全局）。

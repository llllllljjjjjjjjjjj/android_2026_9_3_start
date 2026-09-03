# .claude → .ish 完全无损复刻迁移报告

> 迁移时间：2026-08-28　|　源：`D:\reserve_agent\skills-portable-test`　|　目标：`D:\reserve_agent\`
> 备份：`D:\reserve_agent\.claude_migration_backup_20260828_161443.tar.gz`（SHA256 `2D53136F6DB7CDC17CE018D3B36A2AE3AB95C435C615A73069875C9C23B3F0E1`）

---

## 1. 迁移范围与目标布局

按「终极迁移指令 .claude → .ish」执行。目标根为 `D:\reserve_agent\`，配置目录为
`D:\reserve_agent\.ish\`（项目级 `.ish` 对应源项目级 `.claude` + `.dsh` 双层合并）。

```
D:\reserve_agent\
├── .ish\                        ← 迁移后的配置目录（主层 = 源 .dsh 全部内容）
│   ├── AGENTS.md                ← 源 AGENTS.md（DSH 工作流，路径 .dsh/.claude → .ish）
│   ├── ISH.md                   ← 源 .claude/CLAUDE.md 逐字符转化（规则7）
│   ├── settings.json            ← 源 .claude/settings.json 语义映射（mcpServers 路径 → .ish）
│   ├── mcp-bridge.py            ← 源 .claude/mcp-bridge.py（自动发现 android_mcp，逻辑不变）
│   ├── README.md                ← 源 README-DSH.md 转化
│   ├── pack.ps1                 ← 源 pack.ps1（路径 .dsh/.claude → .ish）
│   ├── strings.txt              ← 0 字节原样
│   ├── skills/                  ← 源 .dsh/skills（8 个技能包，whenToUse 保留）
│   ├── mcp/                     ← 源 .dsh/mcp（cordis.mcp.patch.yml 重新生成、工具索引）
│   ├── tools/                   ← 源 .dsh/tools（env.ps1、TOOLS.md）
│   ├── scripts/                 ← 源 .dsh/scripts（setup-ish.ps1 等 8 个脚本）
│   ├── claude/                  ← 源 .claude 完整镜像（155 文件逐字节一致，兼容层）
│   ├── commands/ agents/ hooks/ plugins/ templates/ presets/ state/
│   │                            ← 空目录占位（源无这些组件，见 EMPTY-DIRS.md）
│   └── MIGRATION-REPORT.md      ← 本文件
├── android_mcp\                 ← 复制（544.7 MB，MCP 服务器代码，规则12）
├── tools\                       ← 复制（136.5 MB，jadx/apktool/so-reverse 工具链）
├── projects\                    ← 复制（1255.6 MB，逆向项目数据）
├── .venv-frida-16.5.7\          ← 复制（119 MB，Frida venv）
├── .venv-frida-16.7.19\         ← 复制（115 MB，Frida venv）
└── .claude_migration_backup_20260828_161443.tar.gz   ← 源配置备份（规则29）
```

## 2. 源目录清单与大小（skills-portable-test）

| 条目 | 类型 | 大小 | 处理 |
|------|------|------|------|
| `.claude/` | 配置层 | 9.55 MB | 逐字节镜像 → `.ish/claude/` |
| `.dsh/` | 配置层 | 9.24 MB | 主层迁移 → `.ish/`（路径改写） |
| `AGENTS.md` | 文档 | 11 KB | 转化 → `.ish/AGENTS.md` |
| `README-DSH.md` | 文档 | 3.5 KB | 转化 → `.ish/README.md` |
| `pack.ps1` | 脚本 | 2.5 KB | 转化 → `.ish/pack.ps1` |
| `strings.txt` | 数据 | 0 B | 原样 → `.ish/strings.txt` |
| `android_mcp/` | MCP 代码 | 544.7 MB | 复制 → `D:\reserve_agent\android_mcp\` |
| `tools/` | 工具链 | 136.5 MB | 复制 → `D:\reserve_agent\tools\` |
| `projects/` | 数据 | 1758 MB | 复制 → `D:\reserve_agent\projects\` |
| `.venv-frida-16.5.7/` | 依赖 | 119 MB | 复制 → 目标根同级 |
| `.venv-frida-16.7.19/` | 依赖 | 115 MB | 复制 → 目标根同级 |
| `11111/` | 旧残留 | 8654 MB | **不迁移**（见 §6） |

## 3. 文件系统一致性验证（规则 27a）

| 对比项 | 结果 |
|--------|------|
| 源 `.claude` vs `.ish/claude`（155 文件，SHA-256，排除 .git） | ✅ 逐字节一致 |
| 源 `.dsh/skills` vs `.ish/skills`（非改写文件） | ✅ 逐字节一致 |
| 改写文件（24 个含 .dsh/.claude 引用） | ✅ 归一化后逐字节一致（仅路径替换） |
| `verify-skills.py`（8 技能 frontmatter + 内容漂移） | ✅ 8/8 OK |
| `.ish` 总文件数 | 283（115 .dsh + 155 .claude + 13 新增/转化） |
| `.ish` 总大小 | 18.85 MB |

## 4. 语义转换映射表（规则 6）

| 源 | 目标 | 转换方式 |
|----|------|----------|
| `.dsh/skills/` | `.ish/skills/` | 目录迁移 + 内容路径 `.dsh`→`.ish` |
| `.dsh/mcp/` | `.ish/mcp/` | 迁移；`cordis.mcp.patch.yml` 用 `gen-mcp-config.py --root D:\reserve_agent` 重新生成（4 个 mcp-client 实例，绝对路径指向 `.ish\mcp-bridge.py`，cwd `D:\reserve_agent`） |
| `.dsh/tools/env.ps1` | `.ish/tools/env.ps1` | 路径改写（逻辑基于 `$PSScriptRoot` 自动发现，无需改） |
| `.dsh/scripts/setup-dsh.ps1` | `.ish/scripts/setup-ish.ps1` | 重命名 + 路径改写 |
| `.dsh/scripts/convert-skills.ps1` | `.ish/scripts/convert-skills.ps1` | 源 `.claude\skills`→目标 `.ish\skills`（兼容层→DSH 层） |
| `.dsh/scripts/gen-mcp-config.py` | `.ish/scripts/gen-mcp-config.py` | `.claude`→`.ish`、`.dsh`→`.ish`；ROOT 自动发现不变 |
| `.dsh/scripts/smoke-mcp.py` | `.ish/scripts/smoke-mcp.py` | BRIDGE `.claude`→`.ish` |
| `.dsh/scripts/verify-skills.py` | `.ish/scripts/verify-skills.py` | SRC/DST `.claude`/`.dsh`→`.ish`；反向 strip 适配 |
| `.dsh/scripts/gen-skill-index.py` | `.ish/scripts/gen-skill-index.py` | SRC `.claude`→`.ish/claude`、DST `.dsh`→`.ish` |
| `.dsh/scripts/when-to-use.json` | `.ish/scripts/when-to-use.json` | rewrites 文本 `.dsh`/`.claude`→`.ish` 语义 |
| `.claude/settings.json` | `.ish/settings.json` | permissions/model/effortLevel 逐字段复制；`mcpServers.args` 路径 `.claude/mcp-bridge.py`→`.ish/mcp-bridge.py` |
| `.claude/mcp-bridge.py` | `.ish/mcp-bridge.py` | 逻辑不变（基于 `__file__` 自动发现 `android_mcp/`）；注释 `.claude`→`.ish` |
| `.claude/CLAUDE.md` | `.ish/ISH.md` | 逐字符 + 路径替换（规则7） |
| `.claude/skills/` | `.ish/claude/skills/` | 原样镜像（兼容层） |
| AGENTS.md | `.ish/AGENTS.md` | 路径 `.dsh`→`.ish`、`.claude`→`.ish/claude`、兼容层标注修正 |
| README-DSH.md | `.ish/README.md` | 同上 |

## 5. 路径替换统计（规则 20/21）

- **替换范围**：`.dsh\` → `.ish\`、`.dsh/` → `.ish/`、`.claude\mcp-bridge.py` → `.ish\mcp-bridge.py`、
  `.claude\skills` → `.ish\claude\skills`（兼容层引用语义）、绝对路径 `D:\reserve_agent\skills-portable-test\...` → 无残留。
- **批量改写文件数**：24 个（mcp/scripts/tools/skills 内文本文件）。
- **语义修正**：darwin-skill（通用 runtime-neutral 技能）的 `~/\.claude/skills/` 生态引用按规则 20
  「仅替换指向配置目录的引用，不改变用户数据中的自然语言」保留原样；兼容层 `claude/` 内全部引用
  原样保留（它是 Claude Code 兼容层文档，`.claude` 引用是其自身语义）。
- **刻意保留**：`mcp/README.md` 中 `%USERPROFILE%\.dsh` 为 DSH 引擎 home（规则 18 环境依赖，非本配置目录）；
  维护记录中的历史 `.claude` 字样（用户数据自然语言）。
- **二进制文件**：无硬编码 `.claude` 路径需要 patchelf/sed 修补（darwin-skill/.git 内部 pack 为 git 对象，无需改写）。

## 6. 无法完全复刻项目（规则 28）

| 项目 | 原因 | 替代方案 |
|------|------|----------|
| `11111/`（8.6 GB） | 源作者在 `pack.ps1` 中标注为 **old duplicate**（旧重复副本），默认排除、仅 `-Legacy` 才打包；内容已被现行 `.claude`/`.dsh`/`android_mcp` 覆盖 | 不迁移。如确需保留，运行 `& .\pack.ps1 -Destination ... -Legacy` 或手动 robocopy |

## 7. 功能验证（规则 27b）

| 项 | 结果 |
|----|------|
| MCP 握手冒烟 `smoke-mcp.py reverse_index`（initialize→tools/list→ping） | ✅ 通过，8 工具列出，`project_root=D:\reserve_agent` |
| 技能发现（8 个 SKILL.md frontmatter: name/description/whenToUse） | ✅ 全部有效 |
| `gen-mcp-config.py --root D:\reserve_agent` 重新生成 | ✅ 4 个 mcp-client 实例 |
| `settings.json` JSON 解析 | ✅ 有效 |
| `cordis.mcp.patch.yml` YAML 解析 | ✅ 有效（4 entries） |
| Python 语法（6 个脚本 + mcp-bridge.py） | ✅ 全部通过 |
| PowerShell 语法（setup-ish/convert-skills/env/pack） | ✅ 全部通过 |
| `verify-skills.py` 内容漂移校验 | ✅ 8/8 OK |

> 真机/设备相关验证（adb 连接、frida server）依赖物理设备，本环境未执行——配置与源一致，基线
> serial `9C181EC3BF7E0D`、frida 路径、env 变量均原样保留。

## 8. 备份与回滚（规则 29-31）

- **备份**：`D:\reserve_agent\.claude_migration_backup_20260828_161443.tar.gz`（SHA256
  `2D53136F6DB7CDC17CE018D3B36A2AE3AB95C435C615A73069875C9C23B3F0E1`，保留 ≥30 天）。
- **回滚**：删除 `D:\reserve_agent\.ish\`、`android_mcp\`、`tools\`、`projects\`、
  `.venv-frida-16.5.7\`、`.venv-frida-16.7.19\` 即可完全恢复（源 `skills-portable-test` 全程只读未动）。
- 源目录 `D:\reserve_agent\skills-portable-test` 未被修改（git 状态保持迁移前）。

## 9. 后续使用（规则 32-33，增量同步）

```powershell
# 在新根启用 MCP（生成并合并到 DSH profile）
cd D:\reserve_agent
python .ish\scripts\gen-mcp-config.py --profile web

# 技能变更后反向同步兼容层
& .ish\scripts\convert-skills.ps1

# 验证
python .ish\scripts\verify-skills.py
python .ish\scripts\smoke-mcp.py reverse_index
```

源 `skills-portable-test` 若继续使用，可后续配置增量同步（robocopy /MIR 或文件监听）；当前为一次性无损迁移。

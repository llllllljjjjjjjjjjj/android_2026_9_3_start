# 便携工具套件（tools/）— DSH 使用说明

> 先执行 `. .\android_mcp\scripts\env.ps1`（或让 DSH 会话自动执行），把 jadx / apktool /
> bundled adb 加入 PATH，并设置 `ANDROID_MCP_*` 环境变量。

## 工具清单

| 工具 | 路径 | 说明 |
|------|------|------|
| jadx 1.5.3 | `tools\jadx\bin\jadx.bat` | DEX/APK 反编译（`jadx -d <out> <apk/dex>`），`jadx-gui.bat` 图形界面 |
| apktool 3.0.3 | `tools\apktool\apktool.bat` | 资源解码/重打包（`apktool d <apk> -o <dir>` / `apktool b <dir>`） |
| ADB（bundled） | `android_mcp\toolchain\bin\windows\platform-tools\adb.exe` | 统一 ADB 入口（MuMu 仅 fallback），MCP 与 skill 均走此路径 |
| frida 客户端 | `.venv-frida-16.5.7\` / `.venv-frida-16.7.19\` | 与真机 server **严格版本对齐**（见 AGENTS.md Frida 矩阵） |
| so-reverse | `tools\so-reverse\` | native 分析占位（ida64.bat 入口；Ghidra/radare2/blutter 需自行准备） |

## 约定

- **ADB 统一**用 bundled `adb.exe`，禁止裸 `adb`（PATH 可能指向别的版本）。
- **PowerShell 多命令**用 `;` 分隔（MCP adb_shell 里同样）。
- 反编译产物统一进 `projects/<target>/decompiled/`，索引用
  `mcp__reverse_index__index_project`。
- 脚本语言：MCP/skill 脚本用 python；临时自动化用 PowerShell。

## 环境变量（ANDROID_MCP_*）

| 变量 | 默认 | 说明 |
|------|------|------|
| ANDROID_MCP_PROJECT_ROOT | 项目根 | 强制项目根 |
| ANDROID_MCP_PYTHON | python | MCP server 解释器 |
| ANDROID_MCP_FRIDA_DEVICE | 9C181EC3BF7E0D | 真机 serial |
| ANDROID_MCP_ALLOW_EMULATOR | 0 | 禁止模拟器 |
| ANDROID_MCP_REMOTE_PATCHED_FRIDA | /data/local/tmp/florida-server | 魔改 frida server 设备端路径 |
| ANDROID_MCP_PATCHED_FRIDA_SERVER | — | 本地 bundled server 文件（可选） |

## 换电脑

把 `tools/`、`android_mcp/`、`.venv-frida-*/` 整体复制过去，按 `AGENTS.md` §7.2
检查路径逐项核对；需要重生成 MCP 绝对路径配置时手动
`python android_mcp\scripts\gen-mcp-config.py --profile web`。

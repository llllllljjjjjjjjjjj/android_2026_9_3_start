# DSH MCP 接入说明（mcp-client）

本目录把 `android_mcp/servers/*`（4 个自建 MCP server）转成 DSH 原生插件配置。

## 原理

DSH 通过 `@deepseek-ai/dsh-mcp-client` 插件连接外部 MCP server。每个插件实例
对应一个 server（stdio 传输），工具注册为 `mcp__<serverName>__<rawName>`。
插件行合并进活动 profile 的 `cordis.patch.yml`
（`%USERPROFILE%\.dsh\profiles\<name>\cordis.patch.yml`，DSH 引擎 home 由 `DSH_HOME` 指定）。

入口统一走 `android_mcp\mcp-bridge.py`：自动定位 `android_mcp/`、把
`android_mcp/common` 与 `toolchain/python/vendor` 加入 PYTHONPATH、
把 bundled platform-tools 加入 PATH —— 无需硬编码绝对路径。

## 文件

| 文件 | 作用 |
|------|------|
| `generated/cordis.mcp.patch.yml` | 已生成、可直接合并的插件补丁（绝对路径） |
| `mcp-tools-index.md` | 每个 server 暴露的工具清单（注册名 `mcp__<serverName>__<tool>`） |
| `README.md` | 本说明 |

## 生成 / 合并（手动）

```powershell
# 生成并合并到 web profile（合并前自动备份 cordis.patch.yml.bak）
python android_mcp\scripts\gen-mcp-config.py --profile web

# 只生成，不写 profile
python android_mcp\scripts\gen-mcp-config.py

# 卸载（移除本包生成的 mcp-* 条目）
python android_mcp\scripts\gen-mcp-config.py --profile web --uninstall
```

合并前自动备份原 `cordis.patch.yml` 为 `cordis.patch.yml.bak`。

## 生效

重启 DSH（或重载插件）后生效。工具以 `mcp__<serverName>__<tool>` 出现在工具目录。
`charles` 需要 Charles Proxy GUI 开启 Web Interface（默认 8888）才有数据；
`frida_orchestrator` 需要真机（基线见 `AGENTS.md`）。

## 自定义

改环境变量后重新生成：

```powershell
$env:ANDROID_MCP_PYTHON = "C:\path\to\python.exe"        # 指定解释器
$env:ANDROID_MCP_FRIDA_DEVICE = "<serial>"                # 换设备
$env:ANDROID_MCP_REMOTE_PATCHED_FRIDA = "/data/local/tmp/f1657"  # 换 frida server
python android_mcp\scripts\gen-mcp-config.py --profile web
```

冒烟测试：`python android_mcp\scripts\smoke-mcp.py reverse_index`（initialize→tools/list→ping 全链路）。

# android_mcp

本目录存放当前项目自建的 Android 真机逆向 MCP。目标是让 Agent 优先通过无 UI MCP 工具直接和真机、Root 文件系统、LSPosed、算法助手、Frida RPC 通信，避免截图/点按式操作。

## 已实现 MCP（5 个）

入口统一走 `mcp-bridge.py <serverType>`，工具注册名 `mcp__<serverName>__<tool>`。

| serverName | 重点能力 | 工具数 |
| --- | --- | --- |
| `reverse_index` | jadx/apktool 产物索引、接口/符号/字符串检索、疑似签名函数定位 | 8 |
| `frida_orchestrator` | 真机优先 ADB/Root/Frida 编排、算法助手/LSPosed/HMA/Reqable 非 UI 操作、Frida RPC 算法 oracle | 80 |
| `algo_lab` | 编码识别、请求差分、Hash/HMAC 候选验证、crypto 常量扫描、复现脚本生成 | 10 |
| `charles` | Charles Web Interface 会话读取（需 Charles GUI 开 8888） | 3 |
| `unidbg` | unidbg SO 模拟执行（JPype 直调） | 1 |

## 便携工具链

MCP 使用到的外部工具收拢到 `D:\reserve_agent\android\android_mcp\toolchain`：

```text
toolchain/bin/windows/platform-tools/adb.exe
toolchain/bin/windows/platform-tools/AdbWinApi.dll
toolchain/bin/windows/platform-tools/AdbWinUsbApi.dll
toolchain/device/frida/florida-server        # 16.5.9 魔改免杀
toolchain/apks/device-tools/*.apk            # HMA/LSPosed/TrustMeAlready/APatch/gnirehtet 等
toolchain/python/vendor/frida/
```

算法助手配置 `/data/system/junge/<pkg>/`（目录 0700 / 文件 0600）必须属主 `system:system`。`algorithm_aide_write_json`/`set_appswitch`/`write_frida_script` 已自动处理（`owner=system:system` + `_fix_junge_dir_owner`），回归测试 `tests/test_algorithm_aide_owner.py`。

通用 `root_ops.root_push_file` 从目标文件/最近已存在祖先继承属主，并对新建目录一起 `chown`（避免落 root:root），回归测试 `tests/test_root_push_owner_fallback.py`。

如需临时覆盖可设置环境变量：

```powershell
$env:ANDROID_MCP_ADB = "D:\path\to\adb.exe"
$env:ANDROID_MCP_ALGO_AIDE_APK = "D:\path\to\algorithm-aide.apk"
$env:ANDROID_MCP_PATCHED_FRIDA_SERVER = "D:\path\to\florida-server"
$env:ANDROID_MCP_REMOTE_PATCHED_FRIDA = "/data/local/tmp/florida-server"
```

## 换电脑/换设备后的推荐流程

1. 把整个项目目录复制到新电脑。
2. 准备 Python 环境，确保能运行 MCP server；Frida Python 包从 `android_mcp/toolchain/python/vendor/frida` 优先加载。
3. 连接真机；USB 连接用 `adb_devices`，TCP 连接先 `adb_connect`。
4. `toolchain_status` 确认 MCP 使用 `android_mcp/toolchain` 内的工具。
5. `bootstrap_device_toolchain` 自动装算法助手、推/起 florida-server、返回健康状态。
6. 后续优先用 `package_components`、`algorithm_aide_*`、`lsposed_*`、`hma_*`、`root_*`、`sqlite_query_root`、`frida_rpc_call`。

## frida_orchestrator 重点工具

```text
toolchain_status / bootstrap_device_toolchain / device_health
adb_devices / adb_connect / adb_shell / adb_root_shell / adb_forward / adb_reverse
pull_package_apk / analyze_pulled_apks / package_components
content_query / content_insert / content_update / content_delete / content_call
intent_start_activity / intent_broadcast / intent_start_service / intent_stop_service
root_ls / root_read_file / root_pull_file / root_push_file / sqlite_query_root
lsposed_query_config / lsposed_list_modules / lsposed_set_scope / lsposed_set_module_enabled
algorithm_aide_read_json / algorithm_aide_write_json / algorithm_aide_set_appswitch
algorithm_aide_write_frida_script / algorithm_aide_log_db_query
hma_read_config / hma_write_config / hma_apply_template_to_scope
push_patched_frida_server / start_patched_frida_server / patched_frida_status
frida_devices / frida_ps / generate_frida_rpc_template / frida_rpc_call
reqable_status / android_proxy_set / android_proxy_clear
tcp_probe_device / http_probe_forwarded
screenshot_save / ui_dump / tap / swipe / input_text / press_key  # 仅 fallback
```

## 当前真机基线

```text
serial: 9C181EC3BF7E0D
model: Pixel 4 (flame)
abi: arm64-v8a
Android: 10 / SDK 29
root: Magisk su 可用
patched frida-server: /data/local/tmp/florida-server, 16.5.9（自报 16.5.10-dev.0）
回退: /data/local/tmp/f1657 (16.5.7) / frida-server (16.7.19)
```

## 已确认的非 UI 通信面

```text
AlgorithmAidePro:
  package:  com.junge.algorithmAidePro
  provider: content://algorithmAidePro/<pref>
  config:   /data/system/junge/<target>/config.json
  switch:   /data/system/junge/AppSwitch.json
  logs:     /sdcard/Android/media/<target>/database/algorithmAidePro.db

HideMyApplist:
  package:  com.tsng.hidemyapplist
  provider: content://com.tsng.hidemyapplist.ServiceProvider
  config:   /data/user/0/com.tsng.hidemyapplist/files/config.json

LSPosed:
  package: org.lsposed.manager
  db:      /data/adb/lspd/config/modules_config.db

Reqable:
  package:    com.reqable.android
  VpnService: com.reqable.android/.NetbareVpnService
  proxy:      android_proxy_set / android_proxy_clear
```

## 快速自测

离线冒烟（无需设备）：

```powershell
python android_mcp\scripts\smoke-mcp.py reverse_index
python android_mcp\scripts\smoke-mcp.py frida_orchestrator
python android_mcp\scripts\smoke-mcp.py algo_lab
python android_mcp\scripts\smoke-mcp.py charles
python android_mcp\scripts\smoke-mcp.py unidbg
```

离线回归：

```powershell
python android_mcp\tests\smoke_test_mcp.py
python android_mcp\tests\test_mcp_timeout_hardening.py
python android_mcp\tests\test_algorithm_aide_owner.py
python android_mcp\tests\test_root_push_owner_fallback.py
python android_mcp\tests\test_frida_ps_bridge_import.py
```

# MCP 工具索引（DSH 注册名：mcp__<serverName>__<tool>）

DSH 加载后，以下工具会以 `mcp__reverse_index__index_project` 这类名字出现在工具目录。

## mcp__reverse_index（reverse-index-mcp，阶段2 静态分析）

索引 jadx/apktool 反编译产物，支撑 API/符号/字符串检索：

| 工具 | 用途 |
|------|------|
| index_project | 为 projects/<target> 建立反编译产物索引 |
| search_code | 源码关键字检索 |
| search_strings | 字符串检索 |
| find_endpoint | 找 URL 端点 |
| find_symbol | 找类/方法/字段符号 |
| find_references | 找引用 |
| list_suspicious_sign_methods | 列出可疑签名方法 |
| open_source | 打开源码文件 |

## mcp__frida_orchestrator（frida-orchestrator-mcp，阶段1/4 动态编排，80 工具）

ADB / Root / Frida / 算法助手 / LSPosed / HMA / Reqable 非 UI 编排。按分组：

- 设备与工具链：`adb_devices` `adb_shell` `adb_root_shell` `device_health`
  `toolchain_status` `adb_connect` `bootstrap_device_toolchain` `adb_forward` `adb_reverse`
- 应用管理：`current_app` `start_app` `stop_app` `clear_app` `install_apk`
  `package_info` `pull_package_apk` `analyze_pulled_apks` `package_components`
  `install_bundled_reverse_apks` `list_reverse_apps`
- Frida：`frida_devices` `frida_ps` `push_patched_frida_server`
  `patched_frida_status` `start_patched_frida_server` `stop_patched_frida_server`
  `generate_hook_template` `start_frida_hook` `list_frida_sessions`
  `read_frida_log` `stop_frida_session` `generate_frida_rpc_template` `frida_rpc_call`
- Root 文件：`root_ls` `root_read_file` `root_pull_file` `root_push_file`
  `sqlite_query_root` `backup_app_data`
- 算法助手（Algorithm Aide）：`setup_algorithm_aide` `algorithm_aide_status`
  `algorithm_aide_list_prefs` `algorithm_aide_read_pref` `algorithm_aide_query_config`
  `algorithm_aide_put_config` `algorithm_aide_read_json` `algorithm_aide_write_json`
  `algorithm_aide_set_appswitch` `algorithm_aide_write_frida_script`
  `algorithm_aide_log_db_query`
- LSPosed：`lsposed_status` `pull_lsposed_db` `lsposed_query_config`
  `lsposed_list_modules` `lsposed_set_module_enabled` `lsposed_set_scope`
- HMA（隐藏应用列表）：`hma_read_config` `hma_write_config` `hma_apply_template_to_scope`
- Android 内容/意图：`content_query` `content_insert` `content_update` `content_delete`
  `content_call` `intent_start_activity` `intent_broadcast` `intent_start_service`
  `intent_stop_service`
- UI 自动化：`screenshot_save` `ui_dump` `tap` `swipe` `input_text` `press_key`
- 抓包治理：`reqable_status` `android_proxy_set` `android_proxy_clear`
  `tcp_probe_device` `http_probe_forwarded`
- 日志：`logcat_tail`

## mcp__algo_lab（algo-lab-mcp，阶段3 算法实验室）

| 工具 | 用途 |
|------|------|
| detect_encoding | 编码识别（hex/base64/url 等） |
| normalize_request | 请求归一化 |
| diff_values / diff_requests | 值/请求差异对比 |
| test_hash_candidates / test_hmac_candidates | Hash/HMAC 候选验证 |
| scan_crypto_constants | 扫描加密常量 |
| analyze_signature_samples | 签名样本分析 |
| generate_python_reproducer | 生成 python 复现器 |
| verify_reproducer | 验证复现器 |

## mcp__charles（charles-mcp，抓包会话读取）

前置：Charles GUI → Proxy → Web Interface Settings → Enable（默认 8888）。

| 工具 | 用途 |
|------|------|
| charles_find | 按 URL 正则查找请求 |
| charles_export | 会话落盘导出 |
| charles_recording | 录制开关 |

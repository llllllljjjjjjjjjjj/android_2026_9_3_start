# Android Armor Breaker 快速开始指南
## 版本: v2.2.6（Qoder 平台适配版）

## 环境要求

### Windows 环境
- **Python 3.8+**：[python.org](https://python.org) 下载安装
- **ADB**：下载 [Android SDK Platform Tools](https://developer.android.com/tools/releases/platform-tools) 或使用模拟器自带
- **Frida Tools**：`pip install frida-tools`
- **Android 设备**：已 root 的真机或模拟器，已连接并启用 USB 调试

### 可选组件（按需安装）
- **Frida 策略**：`pip install frida-tools`，设备上运行 frida-server
- **Root 策略**：设备已 root，`adb root` 可正常执行

## 快速开始

### 1. 环境检查

```powershell
# ADB 统一 bundled 入口（真机优先；MuMu 自带 adb 仅 fallback）
$ADB="android_mcp\toolchain\bin\windows\platform-tools\adb.exe"

# 确认设备连接
& $ADB devices

# 确认 Python 可用
python --version

# 确认 Frida 可用
frida --version
```

### 2. 分析 APK 加固类型

```powershell
python .dsh\skills\android-unpack\scripts\apk_protection_analyzer.py --apk app.apk --verbose
```

输出示例：
```
✅ 检测到 360 加固 (保护级别: HIGH)
✅ 推荐策略: Root 内存提取
✅ 预期成功率: 95%+
```

### 3. 执行脱壳

```powershell
# 方式 1：一键自动编排（推荐）
python .dsh\skills\android-unpack\scripts\unpack_orchestrator.py --package com.target.app --apk app.apk --verbose

# 方式 2：Frida 动态脱壳（无加固/轻度加固）
python .dsh\skills\android-unpack\scripts\enhanced_dexdump_runner.py --package com.target.app --deep-search --verbose

# 方式 3：Root 内存提取（商业加固：爱加密/梆梆/360/腾讯）
python .dsh\skills\android-unpack\scripts\root_memory_extractor.py --package com.target.app --verbose

# 方式 4：内存快照攻击（应用检测到 Frida 立即崩溃）
python .dsh\skills\android-unpack\scripts\memory_snapshot.py --package com.target.app
```

### 4. 反调试绕过（针对强反调试应用）

```powershell
# 自动检测并绕过
python .dsh\skills\android-unpack\scripts\antidebug_bypass.py --package com.target.app --verbose

# 针对梆梆加固
python .dsh\skills\android-unpack\scripts\bangcle_bypass_runner.py --package com.target.app --verbose
```

## 支持的加固方案

| 加固方案 | 支持状态 | 推荐策略 |
|----------|----------|----------|
| 无加固/基础加固 | ✅ 完全支持 | Frida 动态脱壳 |
| 360加固 | ✅ 完全支持 | Root 内存提取 / Frida |
| 梆梆企业版 | ✅ 完全支持 | Root 内存提取 |
| 爱加密（IJIAMI） | ✅ 完全支持 | Root 内存提取 |
| 腾讯加固 | ✅ 完全支持 | Root 内存提取 / Frida |
| 百度加固 | ✅ 完全支持 | Root 内存提取 |
| 网易易盾 | ✅ 支持（VDEX） | Root 内存提取 |
| 强反调试风格 | ✅ 增强支持 | Root + 反调试绕过 |
| 混合加固 | ⚠️ 部分支持 | 需手动测试 |

## 常见问题

### Q1: Python 找不到模块
```powershell
# 确保从项目根目录运行（即含 .claude/ 的便携包根目录）
cd <项目根目录>
python .dsh\skills\android-unpack\scripts\apk_protection_analyzer.py --apk app.apk
```

### Q2: 设备未连接
```powershell
# 检查设备连接
adb devices
# 确保设备已授权 USB 调试
```

### Q3: Frida 无法工作
```powershell
# 安装 Frida
pip install frida-tools

# 在设备上启动 frida-server（主力魔改 florida-server；MCP 一键：frida-orchestrator-mcp → start_patched_frida_server）
$ADB="android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
& $ADB push android_mcp\toolchain\device\frida\florida\florida-server /data/local/tmp/florida-server
& $ADB shell "su -c 'chmod 755 /data/local/tmp/florida-server'"
& $ADB shell "su -c 'nohup /data/local/tmp/florida-server -D &'"

# 验证
frida-ps -U
```

### Q4: Root 内存提取失败
- 确保设备已 root：`adb shell su -c "echo root_ok"`
- 确保 ADB 有 root 权限：`adb root`
- 检查应用是否已安装并可启动

### Q5: "script has been destroyed" 错误
这是强反调试造成的，解决方法：
```powershell
# 先运行反调试绕过
python .dsh\skills\android-unpack\scripts\antidebug_bypass.py --package com.target.app --protection-type strong_antidebug --verbose
# 再运行脱壳
python .dsh\skills\android-unpack\scripts\root_memory_extractor.py --package com.target.app --verbose
```

## 时间预估

| 操作 | 时间 |
|------|------|
| APK 加固分析 | 10-30 秒 |
| Frida 脱壳 | 1-3 分钟 |
| Root 内存提取 | 2-5 分钟 |
| 深度搜索 | +1-2 分钟 |
| 反调试绕过 | 1-2 分钟 |

## 验证结果

脱壳完成后，检查输出目录：
```powershell
# 查看提取的 DEX 文件
Get-ChildItem -Path .\*_unpacked -Recurse -Filter "*.dex" | Select-Object FullName, @{N='Size(MB)';E={[math]::Round($_.Length/1MB,2)}}

# 用 jadx 验证
tools\jadx\bin\jadx.bat -d dex_verify .\*_unpacked\*.dex
```

## 获取帮助

```powershell
# 查看各脚本的帮助
python .dsh\skills\android-unpack\scripts\apk_protection_analyzer.py --help
python .dsh\skills\android-unpack\scripts\root_memory_extractor.py --help
python .dsh\skills\android-unpack\scripts\antidebug_bypass.py --help
```

---

**提示**：所有脚本支持 `--language zh-CN` 参数切换中文输出。

*文档版本: v2.2.6-qoder*
*更新日期: 2026-04-30*

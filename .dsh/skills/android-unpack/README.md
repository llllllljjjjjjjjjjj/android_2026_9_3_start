# Android Armor Breaker v2.2.6 - Android APK 脱壳 & 加固破解工具

> **Qoder 平台适配版** — 基于 Frida 动态注入 + Root 内存静态分析 + 智能 DEX 提取，针对商业级到企业级 Android 应用保护方案。

Android 应用护甲破坏者 - 提供 **APK 加固分析** 与 **DEX 智能提取** 的完整解决方案。

**关键词**: Android APK脱壳, 加固破解, Frida脱壳, DEX提取, 反调试绕过, 内存提取, 逆向工程, 安全研究, Android逆向, 移动安全

## 核心特性

### 功能特性
- ✅ **APK 加固分析** - 静态分析 APK 文件，识别加固厂商和保护级别
- ✅ **环境检查** - 自动检查 Frida 环境、设备连接、应用安装状态、Root 权限
- ✅ **智能脱壳** - 根据保护级别自动选择最佳脱壳策略
- ✅ **实时监控界面** - 追踪 DEX 文件提取过程，实时显示进度
- ✅ **DEX 完整性验证** - 验证生成的 DEX 文件完整性和有效性
- ✅ **增强功能** - 应用预热机制、多次脱壳尝试、动态加载检测、完整性深度验证

### 商业加固对抗
- ✅ **Root 内存提取** - 直接读取 `/proc/<PID>/mem`，完全绕过爱加密、梆梆等商业加固（95%+ 成功率）
- ✅ **VDEX 格式处理** - 自动检测并提取网易易盾 VDEX 格式中的 DEX 文件
- ✅ **反调试增强** - Thread.stop() 拦截、/proc 文件隐藏、Frida 特征隐藏、时序随机化
- ✅ **梆梆专用绕过** - 针对梆梆加固的专项绕过脚本

## 支持的加固方案

- ✅ 360 加固
- ✅ 梆梆企业版
- ✅ 爱加密（IJIAMI）
- ✅ 腾讯加固
- ✅ 百度加固
- ✅ 网易易盾（VDEX 格式）
- ⚠️ 混合加固（360+腾讯等，当前技术限制）

## 快速开始

### Windows 环境安装

```powershell
# 1. 安装 Python 依赖
pip install frida-tools

# 2. ADB 用 bundled platform-tools（真机优先；模拟器自带 adb 仅 fallback）
# 路径：android_mcp\toolchain\bin\windows\platform-tools\adb.exe

# 3. 设置环境变量（ADB 统一入口）
$env:Path = "<项目根>\android_mcp\toolchain\bin\windows\platform-tools;" + $env:Path
```

### 基本使用

```powershell
# 分析 APK 加固类型
python .dsh\skills\android-unpack\scripts\apk_protection_analyzer.py --apk app.apk --verbose

# 一键脱壳（自动选择策略）
python .dsh\skills\android-unpack\scripts\unpack_orchestrator.py --package com.target.app --apk app.apk --verbose

# Root 内存提取（商业加固首选）
python .dsh\skills\android-unpack\scripts\root_memory_extractor.py --package com.target.app --verbose

# 反调试绕过 + 脱壳
python .dsh\skills\android-unpack\scripts\antidebug_bypass.py --package com.target.app --verbose
python .dsh\skills\android-unpack\scripts\enhanced_dexdump_runner.py --package com.target.app --verbose
```

## 技术突破

1. **Root 内存权限修改** - 突破 `PROT_NONE` 内存保护，解决访问违规问题
2. **Frida 特征隐藏** - 重命名文件、非标准端口、函数名混淆，避免脚本销毁
3. **反调试绕过** - 分阶段注入，突破企业级反调试保护（Thread.stop()、/proc 扫描、ptrace 检测）
4. **深度搜索模式** - 从 1 个静态 DEX 发现 100+ 个运行时 DEX
5. **完整性深度验证** - CRC32、SHA-1、MD5 多维度校验
6. **VDEX 格式提取** - 从网易易盾 VDEX 格式中提取完整 DEX 文件
7. **内存静态分析** - 不依赖 Frida，直接读取 `/proc/<PID>/mem`，完全绕过应用层检测

## 成功率参考

| 加固厂商 | Frida | 增强 Frida | Root 内存 | 推荐 |
|----------|-------|-----------|----------|------|
| 无加固 | 98% | 98% | 95% | Frida |
| 360 加固 | 80% | 85-90% | **95%+** | Root |
| 爱加密 | 30-50% | 70-85% | **95%+** | Root |
| 梆梆 | 10-20% | 50-65% | **90%+** | Root |
| 腾讯加固 | 75% | 80-85% | **95%+** | Root |
| 网易易盾 | 0-10% | 15-25% | **85%+** | Root+VDEX |

## 许可证

MIT License

## 支持

如有问题或建议，请通过 Qoder 社区反馈。

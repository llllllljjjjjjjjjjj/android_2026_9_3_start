# Android 逆向便携工作台（DSH 版）

Android APP 逆向工程分析工作台，覆盖 APK 反编译、加固脱壳、协议签名逆向、动态调试、风控对抗全链路。以 DeepSeek Harness（DSH）为运行时，规则唯一源是项目根 `AGENTS.md`，技能唯一源是 `.dsh/skills/<name>/SKILL.md`。

## 真机基线

| 项 | 值 |
|----|-----|
| 设备 | Pixel 4 (flame) |
| Serial | `9C181EC3BF7E0D` |
| 系统 | Android 10 / SDK 29 / arm64-v8a |
| Root | Magisk + Zygisk |
| Frida 主 server | `/data/local/tmp/florida-server`（16.5.9，魔改免杀） |
| Frida 回退 | `/data/local/tmp/f1657`（16.5.7 官方） |
| Frida 备 | `/data/local/tmp/frida-server`（16.7.19 官方） |

## 目录结构

```
android/
├── AGENTS.md                 # DSH 项目级全局指令（唯一源）
├── README.md                 # 本文件
├── .dsh/
│   ├── skills/               # 8 个技能
│   ├── memory/               # 记忆真源
│   ├── plans/                # 分析计划
│   └── scripts/              # 维护脚本
├── android_mcp/              # 5 个自建 MCP（server + bridge + toolchain）
├── tools/
│   ├── jadx/  apktool/       # APK/Java 层
│   ├── so-reverse/           # native SO 套件
│   └── unidbg-boot-server/
├── downloads/                # 第三方工具安装包中转
├── hooker/                   # 通用可复用 Frida 库
├── _archive/                 # 归档
├── .venv-frida-16.5.7/       # Frida 客户端（16.5.x）
├── .venv-frida-16.7.19/      # Frida 客户端（16.7.x）
└── projects/                 # 各逆向目标（自包含模板）
    └── <target>/             # apk/decompiled/hooks/scripts/so_analysis/capture/artifacts/docs/README.md
```

## Skills（8 个）

| Skill | 职责 |
|-------|------|
| android-recon | 侦察/静态分析（入口） |
| android-unpack | 脱壳/加固破解 |
| android-dynamic | 动态调试/Frida/SSL/SO |
| protocol-signature-reverser | 签名/协议算法还原 |
| reverse-skill-evolver | 进化逆向 skill（元） |
| risk-control-adversary | 风控/请求策略 |
| darwin-skill | 通用 skill 优化框架 |


## MCP 服务器

自建 5 个（走 `android_mcp\mcp-bridge.py`，工具注册名 `mcp__<serverName>__<tool>`）：

| serverName | 工具数 | 能力 |
|------------|--------|------|
| reverse_index | 8 | 反编译产物索引、接口/符号检索 |
| frida_orchestrator | 80 | ADB/Root/Frida 编排、算法助手/LSPosed/HMA 无 UI |
| algo_lab | 10 | 编码识别、Hash/HMAC 候选验证 |
| charles | 3 | Charles 会话读取 |
| unidbg | 1 | SO 模拟执行 |

通用 7 个：`js-reverse-mcp`、`adspower-browser`、`ida-pro-mcp`、`reqable`、`wiremcp`、`wedecode`、`sequential-thinking`。

## 工具链（已就位）

| 工具 | 版本/位置 |
|------|-----------|
| jadx | 1.5.3 · `tools\jadx\bin\jadx.bat` |
| apktool | 3.0.3 · `tools\apktool\apktool.bat` |
| radare2 | 6.1.6 · `tools\so-reverse\radare2\bin\` |
| Ghidra | 12.1.2 · `tools\so-reverse\ghidra\ghidraRun.bat`（需 JDK17） |
| NDK | r26c · `tools\so-reverse\android-ndk-r26c\` |
| blutter | `tools\so-reverse\blutter\blutter.py` |
| Il2CppDumper | `tools\so-reverse\il2cppdumper\`（需 dotnet 编译） |
| QBDI | 0.12.1 aarch64 · `tools\so-reverse\qbdi\` |
| LinxerUnpacker | `tools\so-reverse\linxerunpacker\linxerUnpacker.exe` |
| IDA Pro | 9.2 · `tools\so-reverse\ida64.bat` |
| unidbg | `tools\unidbg-boot-server\` |
| Frida 客户端 | 16.5.7 / 16.7.19（两个 venv） |

## 快速开始

```powershell
# 真机连接
& android_mcp\toolchain\bin\windows\platform-tools\adb.exe devices   # 应见 9C181EC3BF7E0D

# MCP 握手验证
python android_mcp\scripts\smoke-mcp.py reverse_index
python android_mcp\scripts\smoke-mcp.py frida_orchestrator

# 反编译
tools\jadx\bin\jadx.bat -d projects\<target>\decompiled projects\<target>\apk\app.apk

# SO 快速体检
tools\so-reverse\radare2\bin\rabin2.exe -I <lib.so>
```

## 维护记录

- 2026-08-25：从 ish-portable-kit / 1111\22222 融合迁移，规则/skill/MCP/工具全链路对齐 DSH。
- 真机 Root 为 Magisk（非 APatch）；frida 主力 florida-server 16.5.9。

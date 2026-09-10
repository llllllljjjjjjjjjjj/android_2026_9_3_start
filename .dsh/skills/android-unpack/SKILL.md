---
name: android-unpack
description: Android 脱壳与加固破解专项。负责「壳识别 → 策略选择 → 脱壳执行 → DEX/SO 验证」。支持 360/腾讯/百度/梆梆/爱加密/网易易盾等商业加固；提供 Frida 动态脱壳、Root 内存提取、抽取壳 frida 主动调用 dumper、内存快照、反调试绕过、VDEX 提取、以及运行期解密壳的 native SO 代码段脱密（梆梆/爱加密）。触发词：脱壳、加固破解、DEX提取、SO脱密、壳识别、VDEX、爱加密、梆梆、360加固、腾讯加固、网易易盾、Root内存提取、抽取壳、FART、Youpk、BlackDex、主动调用。
whenToUse: 用户提到脱壳、加固破解、DEX 提取、SO 脱密、壳识别、VDEX、抽取壳、FART、Youpk、BlackDex、Root 内存提取时
---

# Android Unpack — 脱壳与加固破解

## 角色与边界

你是脱壳专项。**只做** 一件事：把加固 APK 的真实 DEX（或运行期解密的真实 SO 代码段）取出来并验证。

> 🔴 **边界**：
> - 反编译脱壳后的 DEX、提取 API → 回到 **android-recon**
> - 反调试/反 Frida 是为脱壳服务时在本 skill 处理；若是为「运行期 Hook 业务逻辑」服务 → 交 **android-dynamic**
> - 还原签名算法 → **protocol-signature-reverser**

> ⏺️ **全程风控记录**：风控记录开关 YES 时（AGENTS.md），本 skill 执行全程遇到的风控素材随手记到 `projects/<target>/docs/risk-observations.md`——壳扫的检测面/反调试触发点/spawn-attach 存活差异 + 任何不起眼但对风控对抗有用的点（格式见红线 8）。

```
加固分析（壳识别/级别评估）→ 策略选择 → 脱壳执行（Frida动态/Root内存/抽取壳主动调用/SO脱密/快照）→ DEX/SO 验证 → 🔁 android-recon
```

> **脚本目录**：`.dsh/skills/android-unpack/scripts/`。ADB 统一 bundled `android_mcp\toolchain\bin\windows\platform-tools\adb.exe`（MuMu 仅 fallback）。PowerShell 多命令用 `;`。

> 🧰 **配套 MCP（无 UI 优先，工作流见 [AGNETS.md]）** —— 脱壳处于工作流**阶段 1↔2 之间（有壳时）**：用 `frida_orchestrator` 起 frida-server（`start_patched_frida_server`，主力魔改 florida-server；官方 f1657 回退见 android-dynamic §3.4）、拉内存 dump 与脱出的 dex/so（`root_pull_file`/`root_read_file`）、取壳样本（`pull_package_apk`）、查壳配置（`sqlite_query_root`）。脱壳产物 → `projects/<target>/apk/`，反编译后回 **android-recon** 建索引。

---

## 工具速查

| 脚本 | 用途 |
|------|------|
| `apk_protection_analyzer.py` | 加固类型识别、保护级别（LOW/MEDIUM/HIGH/EXTREME）、推荐策略、预期成功率 |
| `unpack_orchestrator.py` | **一键编排**：自动分析→选策略→执行（推荐首选） |
| `enhanced_dexdump_runner.py` | Frida 动态脱壳（`--deep-search` 深搜更多 DEX；配合抽取壳主动调用） |
| `root_memory_extractor.py` / `_enhanced.py` | Root 内存静态提取（绕过应用层检测，95%+） |
| `memory_snapshot.py` | 内存快照攻击（检测 Frida 即崩溃时） |
| `antidebug_bypass.py` | 反调试绕过（Java/Native/System 三层） |
| `bangcle_bypass_runner.py` / `.js` | 梆梆专用绕过 |
| `frida_memory_scanner.js` | Frida 内存扫描 |
| `tools\so-reverse\linxerunpacker\linxerUnpacker.exe` | **裸 ELF / 自解壳脱壳**（native）：ptrace/memfd dump + PT_LOAD 重建（arm64 真机 + root）。脱出的 .so 用 `tools\so-reverse` 的 Ghidra/radare2 分析（已就位） |

---

# 阶段 1：壳识别

**快速判断**：jadx 打开只有空壳 `classes.dex`（几十 KB）→ 整体壳；类结构完整但方法体空 `nop`/`return` → **抽取壳**（被动 dump 取不到，必须主动调用）。

用 `apk_protection_analyzer.py --apk <target.apk> --verbose`（或 APKiD）识别。**各壳厂商特征 so / 包名 / 推荐策略对照表**见 **[references/packer-catalog.md](references/packer-catalog.md)**。

---

# 阶段 2：脱壳执行

> 环境准备、策略 A-D 完整命令、Root 内存原理、抽取壳主动调用代码、失败分支兜底表见 **[references/unpack-methods.md](references/unpack-methods.md)**。下面是策略选择主干。

## 2.1 环境准备

先 `adb devices` 确认真机 + `echo root_ok` 确认 Root；优先 MCP `start_patched_frida_server` 自动起魔改 florida-server。反 Frida 壳扫进程名时必须**改名 + root 裸启动**。命令见 unpack-methods.md §2.1。

## 2.2 策略选择（核心决策）

```
无加固/基础（95%+）              → 策略A Frida 动态脱壳（最快）
360/腾讯/百度（85-95%）          → 策略A 首选，策略B Root 备选
爱加密/梆梆/网易易盾（10-50%）    → 策略B Root 内存提取首选（95%+，零注入）
强反调试/秒崩                   → 策略C 内存快照；先跑 antidebug_bypass
抽取壳（方法体运行时回填）        → 策略D frida 主动调用（被动 dump 无效）
运行期解密 native 壳（SO 代码段）  → §4 SO 脱密（dd 解密段）
无 Root 设备                   → BlackDex 免 Root 脱壳
```

首选一键编排 `unpack_orchestrator.py`。⚠️ **被动 `dd /proc/pid/mem`（策略B）对整体壳有效、对抽取壳无效**——抽取壳方法体未调用前不在内存，必须走策略 D。各策略完整命令见 unpack-methods.md §2.2。

## 2.3 策略 D：抽取壳主动调用（要点）

用魔改 frida `Java.enumerateLoadedClassesSync()` 枚举全部类 → 对每个类 `getDeclaredMethods()/getDeclaredConstructors()` 强制 ArtMethod resolve（触发壳回填 CodeItem）→ 再跑 `enhanced_dexdump_runner.py --deep-search`；脱出的 DEX 常需 **CodeItem patch-back** jadx 才能解。完整 JS 见 unpack-methods.md §2.3。

## 2.4 失败分支

Frida 被检测崩→先 antidebug_bypass，仍崩改策略B；DEX 空/损→策略C 快照；抽取壳方法体空→策略D+patch-back；爱加密级 spawn SIGKILL/attach 崩 server→**策略B 零注入**或 ZygiskFrida（android-dynamic）；native 壳 is_function=false/高熵→§4；x86_64 模拟器跑 360 白屏→换 ARM 真机；网易易盾→Root+VDEX。完整兜底表见 unpack-methods.md §2.4。

---

# §3 DEX 验证

```powershell
tools\jadx\bin\jadx.bat -d dex_verify <extracted.dex>                          # 单个
tools\jadx\bin\jadx.bat -d merged_out classes.dex classes2.dex classes3.dex    # 多 DEX 合并
```

验证通过（类完整、无 stub、方法体非空）→ 🔁 回到 **android-recon** 做静态分析。

---

# §4 SO 代码段脱密（运行期解密壳：梆梆 / 爱加密 native）

壳把 native .text 磁盘加密、运行期解密到内存可执行段时，目标是 dump 解密段回填 IDA。核心：maps 认准 **rwxp/r-xp 匿名段**（对比磁盘高熵）→ PC 端算好十进制 skip（**防 Android sh 32-bit 溢出，高频必中**）→ `dd if=/proc/pid/mem` → IDA 改段权限 r→rx + add_func 重建。梆梆/爱加密具体打法、SHIFT 对齐坑、IDA 多实例坑见 **[references/so-decryption.md](references/so-decryption.md)**。

---

> 📝 **记录前**：风控记录 YES 时，把脱壳中暴露的**环境检测面**记到 `projects/<target>/docs/risk-observations.md`：壳扫的进程名/maps/挂载/端口/签名比对、反调试触发点、spawn/attach 存活差异；**以及清单外任何你认为对抗风控可能用得上的点（哪怕不起眼）**（格式见红线 8）。

# §5 实战案例（已验证，可复用）

已验证案例（连信梆梆 libzhangxin 内存 dump 脱壳还原 RSA+AES 加密链；ct_client 爱加密 root 零注入正解）与**各加固脱壳成功率表**见 **[references/packer-catalog.md](references/packer-catalog.md)**。

---

# 🚨 红线

1. 禁止在 x86_64 模拟器死磕 360 加固（换 ARM 真机）
2. 抽取壳禁止只做被动内存 dump（必须策略D 主动调用回填）
3. 提取 DEX 必须 jadx 验证后才算成功（类完整 + 方法体非空）
4. 商业加固优先 Root 内存（>动态注入）——**例外：抽取壳被动 dump 取不到方法体，需策略D**
5. ADB 统一 bundled `android_mcp\toolchain\bin\windows\platform-tools\adb.exe`（MuMu 仅 fallback）
6. dump 高 VA 地址段一律 PC 端算十进制 skip（防 shell 32-bit 溢出）
7. 反 Frida 壳：frida-server 必须改名 + root 运行；爱加密级别优先零注入 Root dump
8. 风控记录 YES（AGENTS.md 两开关）时，把脱壳遇到的反调试/反 Frida 风控点记到 `projects/<target>/docs/risk-observations.md`：开关二 YES → 按 E-/F- 动态条目模板记完整条目；仅开关一 YES → 记一行；均 NO → 不记

---

# 文件结构

```
.dsh/skills/android-unpack/   （含全部脱壳脚本）
├── SKILL.md                  # 本文件（name: android-unpack）：工作流主干 + 决策 + 红线
├── references/               # 按需加载的详细手册
│   ├── unpack-methods.md     #   阶段2 策略 A/B/C/D 命令、抽取壳主动调用、失败分支
│   ├── so-decryption.md      #   §4 native SO 代码段脱密（梆梆/爱加密）
│   └── packer-catalog.md     #   壳特征对照表、成功率表、实战案例
├── scripts/                  # 10+ 脱壳脚本（见工具速查）
│   └── i18n/                 # zh-CN / en-US 日志
├── README.md / QUICK_START.md / SECURITY.md     # 配套说明（保留根目录，供 validate_optimizations.ps1 扫描）
├── RELEASE_NOTES_v*.md / _meta.json            # 版本变更日志 / 机器元数据（保留根目录）
```

# 安全提醒
仅用于授权安全研究、自有应用调试、恶意软件分析、教育/CTF。禁止未授权分析、破解付费授权、侵犯隐私。详见 SECURITY.md。

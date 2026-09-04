# Android 逆向工程项目 — DSH（DeepSeek Harness）接入说明

## 项目概述

本项目用于 Android APP 逆向工程分析，包括 APK 反编译、加固脱壳、协议签名逆向、动态调试等。

## 角色

你是 Android 逆向工程专家。**真机优先**，**无 UI 优先**（自建 MCP 直打真机，避免截图点按）。能力按工序分工（对应 4 个 skill）：

- **侦察/静态**（android-recon）：jadx/apktool 反编译、reverse-index-mcp 建索引提 API/调用链、抓包治理（代理端口 / proxy 残留 / 机场上游链 / A14 APEX CA / QUIC / eCapture / fp_stack）、malformation 修复
- **脱壳/加固**（android-unpack）：壳识别、Root 内存 dump 零注入、抽取壳主动调用、SO 代码段脱密、**360 VIP magic 抹除扫描**
- **动态/对抗**（android-dynamic）：Frida Hook、Zygisk 默认注入、反 Frida 三层对抗、**真机 arm64≠MuMu x86_64**、美团系 attach-pid 例外、D-810 无 UI 激活、SSL Pinning、SO 分析
- **签名/协议**（protocol-signature-reverser）：6 路并行 + 策略选择器（含策略 H 传输复刻）+ unidbg + 字节级验证；生命周期绑定→在线兜底；**止损型不得称纯算**

## 已安装 Skills（边界明确，按工序分工）

> 逆向工作流：`android-recon`（入口/侦察）→ 按需转交 `android-unpack` / `android-dynamic` / `protocol-signature-reverser`。

### 1. android-recon —— 侦察与静态分析（总入口）
设备连接（真机优先 Pixel4 / MuMu fallback）、证书持久化（A14 APEX）、jadx/apktool 反编译、API/调用链提取（接 reverse-index-mcp）、抓包治理（代理端口/proxy 残留/机场上游/QUIC/eCapture/fp_stack）、malformation 修复、任务分诊。

触发词：APK 反编译、提取 API、调用链、jadx、apktool、连真机、连模拟器、证书、抓包、抓不到包、真机没网、proxy 残留、机场、QUIC、fp_stack、eCapture、Android 逆向入口。

详细文档：[SKILL.md](.dsh/skills/android-recon/SKILL.md)

### 2. android-unpack —— 脱壳与加固破解
壳识别 → 策略选择 → 脱壳执行（Root 内存零注入 / 抽取壳 frida 主动调用 / SO 代码段脱密）→ DEX/SO 验证。支持 360/腾讯/百度/梆梆/爱加密/网易易盾，含全部可执行脚本。

触发词：脱壳、加固破解、DEX 提取、SO 脱密、壳识别、VDEX、爱加密、梆梆、Root 内存提取、抽取壳、主动调用、FART、Youpk。

详细文档：[SKILL.md](.dsh/skills/android-unpack/SKILL.md)

### 3. android-dynamic —— 动态调试 / Frida 对抗 / SSL / SO
运行期 Frida Hook、Frida 版本兼容、Zygisk 默认注入向量、反 Frida 三层对抗（maps 抹除 / root-dump 零注入）、Root 检测绕过、SSL Pinning 8 方案、SO 分析(IDA/Stalker/Unicorn/D-810)、注册级完整性清单。

触发词：Frida、Hook、动态调试、反检测、注入秒退、ZygiskFrida、quicksparrow、SSL pinning、SO 分析、Stalker、Unicorn、D-810、ecapture。

详细文档：[SKILL.md](.dsh/skills/android-dynamic/SKILL.md)

### 4. protocol-signature-reverser —— 签名/协议算法还原
6 路并行采集 + 策略选择器（含混合加密/在线兜底/fp_stack 传输复刻）+ 字节级验证 + unidbg 补环境。把签名还原成离线纯算；生命周期绑定→在线兜底；止损型须明示未解析字段。

触发词：签名逆向、sign、x-mini、shield、mtgsig、八神、算法还原、协议破解、unidbg、补环境、ct_client、MTOP、生命周期绑定、在线兜底、fp_stack、止损型。

详细文档：[SKILL.md](.dsh/skills/protocol-signature-reverser/SKILL.md)

> 另含元技能 `reverse-skill-evolver`（进化上述逆向 skill）/`risk-control-adversary`(风控相关)。

## 风控记录开关（两个，均默认 NO）

> **两者关系（消除交叉）**：开关二**覆盖**开关一。四核心技能在开关二 YES 时遇到风控点，只按 E-/F- 完整条目记一次，**不重复记开关一的一行**；各处已有的「风控记录 YES 时记」触发点在开关二 YES 时自动升级为完整条目记录。开关一仅用于：开关二 NO 时的轻量观察，或四核心技能之外的环节。

### 开关一：风控观察（轻量一行式）

- **开关**：NO（改 YES 开启；NO 时不记录，保持逆向流程不被打断）
- **记录位置**：`projects/<target>/docs/risk-observations.md`（追加式）
- **格式**：日期 + 信号 + 上下文 + 证据路径（一行）
- **触发信号**（遇到即记）：403/429、验证码、封禁码、返蜜罐数据、频控阈值实测值、环境检测命中（反 Frida/Root/Hook/代理检测）、无效签名或令牌软封、延迟处罚
- **用途**：risk-control-adversary 生成方案时的 A1 资料源

### 开关二：风控动态条目（细致 E-/F- 格式，四核心技能专用）

- **开关**：YES（改 YES 开启）
- **适用**：android-recon / android-unpack / android-dynamic / protocol-signature-reverser
- **原因**：四技能是动态实测（抓包/Hook/运行期观察），证据比静态推测更硬，风控点按 risk-control-adversary 同等粒度沉淀，避免「转接后丢失细节」
- **记录位置**：`projects/<target>/docs/risk-observations.md`（与开关一同文件，用条目区块）
- **格式**：按 risk-control-adversary `references/templates.md` §3.3（E-）/§3.4（F-）字段填写；条目标题加 `[动态]` 前缀，编号用 `E-cand`/`F-cand`（候选）。**关键字段（检测原理/对抗思路/证据等级/置信度/来源）必填，管理字段（操作边界/标签/关联/版本等）收割时由 risk-control-adversary 补全**
- **后续**：risk-control-adversary 生成方案时把这些 `[动态]` 候选条目按 §0.4 准入收割进 L1/L3（动态实测通常直接满足 ≥小样本/已实证门槛）

**动态 E 条目模板**（照着填，完整字段见 templates.md §3.3）：

```markdown
### [动态] E-cand <角度>
- 类型: <主维度>（跨维加 +次维度，如「设备指纹+业务规则风控」）
- 检测原理: <风控方怎么检测；当下只知现象就写「现象: xxx，根因待分析」>
- 对抗思路: <可迁移的策略一句；具体工具/命令/步骤不写，留交叉引用专项 skill>
- 落地工具: <本技能用到的；写专项 skill 具体章节>
- 证据等级: 已实证 / 小样本 / 推测（按 R×N：单次验证 R=1 只能填小样本）
- 置信度: 高 / 中 / 低
- 来源: projects/<target> <YYYY-MM-DD> <抓包/Hook 证据路径>
```

**动态 F 条目模板**（照着填，完整字段见 templates.md §3.4）：

```markdown
### [动态] F-cand <失败场景>
- 触发条件: <什么操作触发>
- 失败特征: <封禁/报错/蜜罐等可观测信号>
- 根因分析: <为什么会失败；当下只知现象就写「现象: xxx，根因待分析」>
- 规避方案: <怎么做避免；可迁移策略，不写具体工具命令>
- 影响等级: 致命 / 严重 / 一般
- 证据等级: 已实证 / 小样本 / 推测（单次验证 R=1 只能填小样本）
- 来源: projects/<target> <YYYY-MM-DD> <证据路径>
```

## MCP 服务器（DSH mcp-client 插件）
项目自带 5 个无 UI 逆向 MCP（位于 [android_mcp/](android_mcp/README.md)），**优先用 MCP 工具直接打真机 / Root / LSPosed / 算法助手 / Frida，避免截图点按式操作**。配置见 `android_mcp/mcp_config.example.json`，统一用 `android_mcp\toolchain\bin\windows\platform-tools\adb.exe`（自带，无需 MuMu 路径）。
自建 MCP 通过 `@deepseek-ai/dsh-mcp-client` 插件接入，配置已合并进
`$DSH_HOME/profiles/<name>/cordis.patch.yml`（生成器：`android_mcp/scripts/gen-mcp-config.py`）。
工具注册名：`mcp__<serverName>__<tool>`。

| serverName |核心能力 | 工具数 |
|------------|------|----------|--------|
| `frida_orchestrator` | 真机优先 ADB/Root/Frida 编排：连设备、拉 APK、查组件、Root 文件/SQLite、算法助手/LSPosed/HMA/Reqable 无 UI 操作、Frida RPC 算法 oracle。**必带** `ANDROID_MCP_TOOL_TIMEOUT=90` | 80 |
| `reverse_index` | 对 `projects/<target>/decompiled/` 建索引：找接口 / 符号 / 字符串 / 疑似签名·加密·token 逻辑 | 8 |
| `algo_lab` | 编码识别、请求规范化/差分、hash/HMAC 候选爆破、crypto 常量扫描、复现脚本生成 + 字节级校验 | 10 |
| `charles` | 官方抓包 MCP。Charles pin `mcp<2`。开抓包前上游链 `127.0.0.1:7892`（OneLite） | 3 |
| `unidbg` | unidbg SO 模拟执行（JPype 直调）、generate | 1 |
| `js-reverse-mcp` | 浏览器 JS 逆向（断点 / 调栈 / 改源）；`playwright` 仅页面操作 | — |
| `ida-pro-mcp` | IDA；D-810 无 UI 激活自查 | — |

**MCP 写设备文件属主**：`algorithm_aide_*` 写 `/data/system/junge/<pkg>/` 必须 `system:system`（目录 0700 / 文件 0600）——三个 writer 已自动处理。通用 `root_push_file` 首写会继承最近已存在祖先属主并对新建中间目录 `chown`（HMA app-uid 配置不再落 root:root）。绕过 MCP 手写才会污染；改源码后必须 Reload Window。

### 标准工作流（4 阶段闭环）

1. **采集 / 侦察 — `frida-orchestrator-mcp`**：`adb_devices`/`adb_connect` 连真机 → 一键 `bootstrap_device_toolchain`（装算法助手、推+起魔改 frida-server）→ `pull_package_apk` / `package_components` / `root_read_file` / `sqlite_query_root` 取目标与 Root 数据。
   > 拉到 APK 后用 jadx/apktool 反编译到 `projects/<target>/decompiled/`（见 android-recon）；**若有壳，先走 android-unpack 脱壳出 dex 再反编译**。
2. **静态定位 — `reverse-index-mcp`**：`index_project` 建索引 → `find_endpoint` / `find_symbol` / `search_strings` / `list_suspicious_sign_methods` 定位签名·加密·token 入口与调用链。
3. **算法假设 — `algo-lab-mcp`**：`analyze_signature_samples` / `detect_encoding` 看样本形态 → `test_hash_candidates` / `test_hmac_candidates` 猜算法与 key → `generate_python_reproducer` + `verify_reproducer` 生成并字节级校验离线复现。
   > 样本来自 phase 1 的抓包（`android_proxy_set` + Reqable/mitmproxy，落 `projects/<target>/capture/`）。传输墙先走 `projects/fp_stack/`。
4. **动态验证 — `frida-orchestrator-mcp`**：`generate_frida_rpc_template` + `frida_rpc_call` 把目标函数当算法 oracle 在线验证；或用算法助手 (`algorithm_aide_*`) / LSPosed (`lsposed_*`) 无 UI 注入比对。

> **这是闭环不是直线**：phase 4 验证失败就回 phase 2/3 修正假设；签名还原主战场是 protocol-signature-reverser，会在 2↔3↔4 之间反复迭代。

### 阶段 ↔ 技能 ↔ MCP

| 阶段 | 技能 | 主用 MCP |
| --- | --- | --- |
| 采集/侦察 + 反编译 | android-recon（入口） | frida-orchestrator-mcp → reverse-index-mcp |
| 脱壳（有壳时） | android-unpack | frida-orchestrator-mcp（Root 内存 / 拉 dex） |
| 静态定位 + 算法假设 | protocol-signature-reverser | reverse-index-mcp + algo-lab-mcp |
| 动态验证 / Frida 对抗 / SSL / SO | android-dynamic、protocol-signature-reverser | frida-orchestrator-mcp |


## 工具链
| 工具 | 路径 | 用途 |
|------|------|------|
| jadx | `tools\jadx\bin\jadx.bat` | DEX/APK 反编译 |
| apktool | `tools\apktool\apktool.bat` | APK 解包/重打包 |
| ADB | `android_mcp\toolchain\bin\windows\platform-tools\adb.exe`（MuMu `nx_main\adb.exe` 仅 fallback） | Android 设备通信 |
| Frida | venv `.venv-frida-16.5.7`(florida-server 16.5.9) / `.venv-frida-16.7.19`(frida-server 16.7.19) | 动态 Hook、内存 Dump、RPC |
| IDA Pro | 配合 ida-pro-mcp（tools\so-reverse\ida64.bat → D:\IDA_Professional_9.2.7） | SO 库深度分析 |
| mobile-mcp / agent-device | `@mobilenext/mobile-mcp`（优先）/ （兜底） | 设备 UI 自动化（仅无 UI MCP 不可达时） |
| Ghidra | GUI `tools\so-reverse\ghidra\ghidraRun.bat` | native .so 反编译（见下方套件） |

## 项目目录结构规范（强制）

路径统一以项目根为基准；`.dsh/skills/` 为 DSH 技能根（引擎识别的唯一 `.dsh` 位置）。

```
项目根目录/                 
├── AGENTS.md                   ← 本文件（DSH 自动注入的项目级全局指令，唯一源）
├── README.md                   ← 项目说明
├── .dsh/                       ← DSH 技能层（仅 .dsh/skills 被引擎识别）
│   ├── skills/                 ← 8 个技能定义（<name>/SKILL.md，自动发现）
│   ├── memory/                 ← 记忆真源（MEMORY/current_task/reverse_principles）
│   ├── plans/                  ← 分析计划
│   └── scripts/                ← 维护脚本（apply_optimization / diagnose 等）
├── android_mcp/                ← MCP 业务层：server + 桥接 + 运维脚本       
├── tools/                      ← jadx / apktool / so-reverse / unidbg-boot-server
├── downloads/                  ← 第三方工具安装包中转（frida-server / 待分析 APK 等）
├── hooker/                     ← 通用可复用 Frida 库（js/ + hooker.py，非项目专属）
├── .venv-frida-16.5.7/         ← Frida Python venv（16.5.x）
├── .venv-frida-16.7.19/        ← Frida Python venv（16.7.x）
├── _archive/                   ← 归档/临时/待分类（move-manifest.txt 记录迁移）
└── projects                    ← 子项目目录（每个目标自包含，见下方模板）
    
```

### 子项目自包含模板（强约束）


每个目标在 `projects/<target>/` 下完全自洽，**禁止再把单项目代码散落到根目录共享桶**：

```
projects/<target>/          ← 各逆向项目按目标分目录（**禁止再把单项目代码散落到根目录共享桶**）
├── apk/                    ← 原始 apk / 拆出的 dex
├── decompiled/             ← jadx / apktool 反编译产物
├── hooks/                  ← 该项目专属 Frida / hook 脚本(js)
├── scripts/                ← 该项目专属 Python（签名复现/分析/RPC）
├── so_analysis/            ← .so + .i64 + IDA 分析
├── capture/                ← 抓包 flows / 日志
├── artifacts/              ← 截图、中间产物、报告 json
├── docs/                   ← 分析笔记 / 进度 / 交接 md
└── README.md               ← 目标说明 + 现状 + 入口（必须有）
```
---

> 目录名一律 ASCII（禁止中文/特殊字符）；按需创建子目录，但 README.md 必须存在。





### native .so 逆向套件：`tools\so-reverse\`（已配置）

与现有工具分层、零运行时冲突（独立子目录 · 不在 PATH）：

- **APK/Java 层**：`tools\jadx\bin\jadx.bat` + `tools\apktool\apktool.bat`
- **native .so 层（已就位）**：
  - radare2 6.1.6：`tools\so-reverse\radare2\bin\`（r2/rabin2/rasm2）
  - Ghidra 12.1.2：`tools\so-reverse\ghidra\ghidraRun.bat`（需 Java 17）
  - NDK r26c：`tools\so-reverse\android-ndk-r26c\`（ndk-build/llvm-readelf/nm/strings）
  - blutter：`tools\so-reverse\blutter\blutter.py`（Flutter）
  - Il2CppDumper：`tools\so-reverse\il2cppdumper\Il2CppDumper.sln`（Unity IL2CPP）
  - QBDI 0.12.1：`tools\so-reverse\qbdi\local\bin\qbdi-template-AARCH64`（arm64 真机）
  - LinxerUnpacker：`tools\so-reverse\linxerunpacker\linxerUnpacker.exe`（看雪工具，ptrace 脱壳，需 root）
- **重度反编译首选 IDA Pro**（`tools\so-reverse\ida64.bat` → `D:\IDA_Professional_9.2.7`）；Ghidra 作二线。

## 使用规范

- 执行 skill 中的脚本前，先确认设备连接状态（`adb devices`）
- 脱壳脚本路径统一为 `.dsh/skills/android-unpack/scripts/`
- **新目标一律按上方模板在 `projects/<target>/` 下创建，不在根目录散落 .py/.js/.apk/截图**
- 反编译产物 → `projects/<项目名>/decompiled/`
- Frida/hook → `projects/<项目名>/hooks/`；Python 脚本 → `.../scripts/`
- 截图、日志、抓包、报告 → `projects/<项目名>/artifacts/`（抓包亦可放 `.../capture/`）
- 通用可复用 hook 放 `hooker/js/`；第三方工具包放 `downloads/`

---
name: android-dynamic
description: Android 动态调试专项。负责运行期 Frida Hook、Frida 版本兼容（含真机 arm64≠MuMu x86_64）、反 Frida 三层检测对抗（Zygisk 默认注入向量 / maps 抹除 / root 内存 dump 零注入逃生门）、spawn-vs-attach（含美团系 attach 例外）、商业加固 hook 层规则（quicksparrow/ANet/360VIP）、Root 检测绕过、SSL Pinning 8 方案选择器、SO 分析（IDA/Stalker/Unicorn 快照/RDTSC/D-810 CFF 含无 UI 激活）、注册级完整性检测清单。内含 APP 安全等级矩阵与「及时止损线」。
whenToUse: 用户提到 Frida、Hook、动态调试、frida检测、反检测、注入秒退、attach崩server、ZygiskFrida、spawn注入、SSL pinning、抓包绕过、SO分析、Stalker、Unicorn、RDTSC、D-810、CFF、native hook、quicksparrow、objection、Florida、ecapture、完整性检测。
---

# Android Dynamic — 动态调试 / Frida 对抗 / SSL / SO

## 角色与边界

你是运行期对抗专项。**只做**：Frida Hook 与反检测、SSL Pinning 绕过、SO 动态分析。

> 🔴 **边界**：
> - 反编译/提取 API/抓包通路 → **android-recon**
> - 取真实 DEX（脱壳）/ native SO 代码段脱密 → **android-unpack**
> - 把 SO 算法还原成纯 Python/离线 → **protocol-signature-reverser**（本 skill 只负责动态定位/trace/RPC，不做纯算实现）

```
🛑 动 Hook 前先过三关：① APP 在安全等级矩阵第几级？② 检测 Frida 吗？③ 选对注入链与绕过方案
```

> ADB 统一 bundled `android_mcp\toolchain\bin\windows\platform-tools\adb.exe`（MuMu `nx_main\adb.exe` 仅 fallback）。真机基线 **Pixel 4 / 9C181EC3BF7E0D / Android 10 arm64 / Magisk + Zygisk**。

> 🧰 **配套 MCP（无 UI 优先，工作流见 [AGENTS.md]）** —— 本 skill = 工作流**阶段 4（动态验证）**，优先用自建 `frida_orchestrator` 而非截图点按：
> - 魔改frida-server 生命周期（MCP 主力管魔改 `/data/local/tmp/florida-server`；官方 f1657 回退；改名裸启动 §3.4）：`start_patched_frida_server` / `patched_frida_status` / `stop_patched_frida_server`；进程枚举 `frida_ps`。
> - 算法 oracle：`generate_frida_rpc_template` + `frida_rpc_call`（把目标函数当在线 oracle 验证）。
> - 无 UI 注入比对：算法助手 `algorithm_aide_*`、LSPosed `lsposed_set_scope`/`lsposed_set_module_enabled`。
> - SO 深度分析仍用 `ida-pro-mcp`（IDA 内 Ctrl+Alt+M 启动）。
> - **native SO 套件（本机 `tools\so-reverse\`，分工详见 [AGENTS.md]**：重度反编译/去混淆**首选 IDA Pro**；二线 Ghidra `ghidraRun.bat`（需 Java 17）；radare2 `rabin2` 快速体检；QBDI `qbdi\local\bin\qbdi-template-AARCH64`（真机 arm64）动态插桩。**全套已就位**。

---

# §1 Frida 版本兼容 + 真机基线（写脚本前必读）（待匹配路径）

🔴 **CHECKPOINT：写任何 Frida 脚本前确认 frida-server 版本与引擎。**

| server（真机） | 版本 | PC 客户端 | 适用 |
|---------------|------|-----------|------|
| `/data/local/tmp/florida-server` | 16.5.9（Florida 魔改免杀，自报 16.5.10-dev.0） | venv `.venv-frida-16.5.7`（**16.5.x↔16.5.x**） | **主力**，改名裸启动（§3.4） |
| `/data/local/tmp/f1657` | 16.5.7（官方） | venv `.venv-frida-16.5.7`（**16.5.x↔16.5.x**） | 官方回退 |
| `/data/local/tmp/frida-server` | 16.7.19（官方） | PC `frida` 16.7.19 | 普通目标 |

> 🔴 **17.x 在硬目标全挂**（XHS 所有模式秒退）；16.7.19 / 16.5.x 才是工作线。

| 触发条件 | 修复 |
|---------|------|
| `Module.findExportByName is not a function`（17.9.1+ 移除） | 改 `Process.findModuleByName('libc.so').findExportByName('fopen')` |
| undetected-frida-server | 只有 `Module.getGlobalExportByName(name, module)`，**参数顺序相反**：`getGlobalExportByName('strstr','libc.so')` |
| 17.x Duktape 语法报错 | **禁用** `===`/`let`/`const`/箭头函数/`String.includes()`/`for...of`；改 `var`/`==`/`indexOf`/普通 `for` |
| `send()` 大数据被截断 | 单条约 16KB 上限 → 分块发送或落盘再 pull（大二进制 dump 见 §5 send-dump） |

```powershell
.\.venv-frida-16.5.7\Scripts\frida.exe -U -f <包名> -l hook.js --no-pause   # spawn（推荐，bypass 在初始化前生效）
.\.venv-frida-16.5.7\Scripts\frida.exe -U <包名> -l hook.js                  # attach 运行中（硬壳禁用，见 §3.4）
```

```javascript
// Java（Duktape 兼容）
Java.perform(function() {
    var T = Java.use("com.example.TargetClass");
    T.targetMethod.implementation = function(a, b) {
        var r = this.targetMethod(a, b);
        console.log("[+] args:", a, b, "ret:", r);
        return r;
    };
});
// Native
var fopen = Process.findModuleByName("libc.so").findExportByName("fopen");
Interceptor.attach(fopen, { onEnter: function(args){ console.log("[+] fopen:", args[0].readUtf8String()); }});
```

---

# §2 APP 安全等级矩阵 + 注入决策

| 等级 | 防御 | 可行操作 | 示例 |
|:----:|------|----------|------|
| L0 | 无 | Java + Native Hook + objection | Bilibili |
| L1 | 基础 Frida 检测 | undetected-frida + Native Hook | Apple Music |
| L2 | 商业加固 ART-hook 检测（quicksparrow `mthook_sign_maps`） | **仅 Native Hook，不碰 Java**（§3.5） | Ele.me / 淘宝闪购 / 盒马 |
| L2 | MS SDK 反枚举 + VMP 反 hook（checksum 0x312768B @ metasec 275064 区，勿 hook）+ 基础 Frida 检测 | spawn/attach 均可行（frida 全程未被杀）；**勿 hook 275064 区 syscall 包装**，函数入口 hook 安全；运行后从进程表反枚举消失 → `adb pidof` 直连 attach(pid)（SF-016）；RPC oracle 全小写方法名 | dy 抖音 38.0.0（八神签名，见 protocol 案例速查） |
| L3 | 启动期 watchdog + 匿名 rwx（爱加密 RASP） | **ZygiskFrida（默认）** 或 root 内存 dump 零注入 | ct_client |
| L3b | 进程级反注入 / 代理自杀（含崩 zygote） | **只允许零注入**（dump/eCapture） | 平安好车主；360VIP 瑞幸 |
| L4 | ART 代码完整性（`Java.perform` 触发 SEGV） | 放弃签名层 Hook，仅调业务 API | XHS |
| L4m | MTGuard 反检测 + Shark 隧道 | **attach pid**（spawn 易触发）；禁刷无效 mtgsig | Keeta / 猫眼 |
| L4d | 代理即断网 + 魔改 boringssl | 魔改 frida **可存活**；抓包用 eCapture 零注入 | 抖音（florida 16.5.9 是 enabler） |
| L5 | RASP 全防御 + 结果完整性 | 放弃 Frida → 转纯协议 | — |

🔴 **CHECKPOINT — 注入向量决策（Zygisk 优先，不是兜底）**：
```
APP 检测 Frida 吗？
├─ 否 → 标准 frida-server（spawn）
├─ 基础 → Florida / undetected-frida（spawn）
├─ ART-hook 检测(quicksparrow) → 仅 Native Hook，Java 一律不碰（§3.5）
├─ 启动期 watchdog/匿名rwx(爱加密级) → ★ZygiskFrida(zygote 注入，§3.3) 或 root 内存 dump 零注入
├─ ART 完整性(XHS级) → 放弃签名层 Hook，仅调业务 API / 转纯协议
└─ 结果完整性 → 放弃 Frida → 纯协议

推荐注入链（硬壳默认）：
  ZygiskFrida（zygote 注入 gadget，结构性绕过 L1 cmdline + L3 ptrace + 启动期 watchdog）
    → on_load=resume + start_up_delay_ms（过一次性启动检测）
    → bypass（§3.2，maps 抹除优先）
    → Hook
普通目标：undetected-frida(spawn) → bypass → Hook
```

> 为什么 Zygisk 提为默认：ct_client 爱加密的攻破靠的是**注入向量改变**（zygote、App 代码之前、零 ptrace），不是 frida 字符串混淆。改 where/when 注入 > 改 frida 特征。

---

# §3 反检测对抗

## 3.1 Root 检测绕过（4 层缺一不可，必须 spawn）

1. **Native 文件检测**：Hook `faccessat`/`access`/`stat`/`fopen` —— 拦 `/system/xbin/su`、`/system/bin/su`、`/sbin/su`、`Superuser.apk`、`/magisk/`。**`fopen` 不能漏**
2. **Java 层**：检测类方法返回 false/0（jadx 搜 `RootBeer`/`isRooted`/`/su`）
3. **GPS/模拟器检测**：返回 0
4. **WebView/完整性**：校验返回 false

## 3.2 反 Frida 三层模型 + 绕过

| 层 | 检测手段 | 绕过（首选 → 降级） |
|----|---------|------|
| L1 进程/命令行 | `/proc/self/cmdline` 找 frida、线程名、`init.svc.adbd` | **重命名 frida-server**（§3.4）+ ZygiskFrida（无 frida 进程）；或 Hook FileReader/Runtime.exec/`__system_property_get` 返回假值 |
| L2 内存签名 | 扫 `/proc/self/maps` 找 `frida`/`gum-js-loop`/`linjector`，匿名 rwx JIT 段 | **maps 抹除（首选，无可扫之物）**：memfd-backed agent load + soinfo 从 linker solist unlink → gum/agent 不再出现在 maps；**降级** 100ms golden window `Memory.scanSync`→清零 |
| L3 ptrace | `ptrace(PTRACE_TRACEME)` 失败=已附加 | **ZygiskFrida 不走 ptrace**（结构性免疫）；或 `Interceptor.replace` 伪造 TRACEME 成功 |

```javascript
// L3 降级：伪造 PTRACE_TRACEME 成功
Interceptor.replace(ptracePtr, new NativeCallback(function(req){
    if (req === 0) return 0;            // Fake PTRACE_TRACEME
    return original_ptrace(req);
}, 'long', ['long','long','long','long']));
```

> ⚠️ **100ms 竞速是降级方案不是主方案**：watchdog 可能在你 hook 之前就扫（爱加密 raw-svc watchdog 用 raw svc 抢先扫 maps 杀 rwx JIT，read-hook 在内容读时根本不触发）。82% 反 Frida 有可利用时序窗口，但剩 18% 没有 → 与其赛跑，不如让 agent 从一开始就不以可识别区域出现（maps 抹除）。匿名 rwx 检测靠 libc hook 从根上做不到，只能换注入向量（Zygisk）或零注入（root dump）。

## 3.3 ZygiskFrida 默认注入（爱加密级 RASP 实证攻破，配置 self-contained）

zygote 注入 gadget，不走 ptrace，在 App 代码前就位，绕过 RASP watchdog：

```
模块：/data/adb/modules/zygiskfrida  (v1.9.0)
配置：/data/local/tmp/re.zyg.fri/
  ├─ config.json           # { targets: ["<包名>"] }
  └─ libgadget.config.so   # gadget 配置：interaction listen + on_load=resume
gadget：frida 17.4.0（QuickJS，★无 Java 桥，只 native hook）
关键参数：
  - interaction = listen + on_load = "resume"   # 用 wait 会卡死
  - start_up_delay_ms = 20000                   # 过启动期一次性检测
连接：
  adb forward tcp:27042 tcp:27042
  重启 App → 等 ~35s → add_remote_device("127.0.0.1:27042") → dev.attach("Gadget")
```

> ⚠️ **坑**：`re.zyg.fri` 常被 relabel 成 `system_file` → root 都写不进 → `chcon u:object_r:shell_data_file:s0 /data/local/tmp/re.zyg.fri/*` 修。
> ⚠️ gadget 是 QJS 无 Java 桥 → 只能 native hook；要 Java 层走别的注入或调业务 API。

## 3.4 spawn-not-attach 硬规则 + 重命名（硬壳必读）

- **硬壳/反调试 App 一律 spawn 不要 attach**：attach 时 frida 用 ptrace 占用主进程 → 反 ptrace 壳挂起超时，**爱加密实测 attach 直接崩 frida-server 本体**（florida 和 new-server 都崩，App 反而存活）——别误判为环境问题。
- **例外：美团系（Keeta / 猫眼）用 attach pid，不要 spawn、不要按包名 attach。** MTGuard 对 spawn 更敏感；猫眼签名桥 `IIVTQYOSF`、Keeta `d0.result()` 都是运行期 attach。Play MinuteMaid 打 `com.google.android.gms.unstable`（ZygiskFrida 要打这个 process，不是主 gms）。
- **重命名过启动期进程名扫描**：壳扫进程名匹配 `frida`/`florida`/`server` 直接杀 → `cp florida-server sysmon_helper`（florida-server→`sysmon_svc`）改名后裸启动存活；frida-server **必须 root 运行**（`su -c nohup`，否则 ptrace 注入失败报 closed）。
- 默认端口 27042 的 spawn 可用；自定义端口（`-l`）会让 USB spawn 报 "need Gadget"。

## 3.5 商业加固 hook 层规则（quicksparrow / ANet）

| 检测/栈 | 机制 | 规则 |
|---------|------|------|
| quicksparrow `mthook_sign_maps`（Ele.me） | 扫 `/proc/self/maps` 找 ART 方法 hook 签名 | `Java.use().implementation=` 改 ART entry 留痕 → 服务端**静默封 API**（症状：hook 装上、App 不崩、滑动不出数据）→ **Java/ART Hook 不可用，仅 Native Hook**（`Interceptor.attach` native 不碰 ART，不被检测） |
| ANet / `libtnet.so`（阿里系） | 核心 MTOP 走 ANet 内部 BoringSSL（符号 strip） | OkHttp hook 完全无效；系统 `libssl` `SSL_read/write` 只抓非核心流量（且 native libssl hook 不触发 quicksparrow，值得做） |

> 判定泛化：Java hook「装上 OK 但 App 静默降级/服务端封」→ 怀疑 native maps-scan ART-hook 检测，转 native 层。
> 360VIP（瑞幸）：**live 拒绝一切进程内注入**（frida/LSPosed/算法助手 → SIGSEGV）。脱壳/取证只允许 Root dump；不要在该机留 new-server。
> 算法助手配置 `/data/system/junge/<pkg>/config.json` 必须 **system:system**（目录 0700 / 文件 0600），因为助手以 system uid 跑。**MCP 已自动搞定**（2026-08-18 修：`algorithm_aide_ops.py` 三个 writer 传 `owner=system:system` + `_fix_junge_dir_owner` 回收目录链），不用再手动 chown。只有绕过 MCP 手写、或早于该修复留下的目录才会是 root:root；判定用 `find /data/system/junge -user root` 应为空，非空就 `chown -R system:system` 修回。
> 通用规则：写「属主非 root 的目录」的配置（app 私有 `/data/user/0/<pkg>/`、system 目录）**别让首写落 root:root**。`root_ops.root_push_file` 现在会先走缺失目录链、再从**最近已存在祖先**继承属主，并对新建中间目录一起 `chown`（2026-08-18）。HMA `hma_write_config` 写 app uid（10270）的 `files/config.json`、以及往 app 私有树里新建子目录，都不会再变 root。junge 仍额外显式传 `owner=system:system`。

## 3.6 及时止损线 + anti-RASP 阶梯（最重要的判断）

🔴 **CHECKPOINT：注入即秒退，先判检测层级再决定投入。爱加密级 ≠ 放弃 Frida；ART 完整性级才真正放弃。**

爱加密级（启动期 watchdog）anti-RASP 阶梯：
```
① 重命名 frida-server + root 运行（过进程名扫描）
② spawn 注入（不 attach；attach 崩 server）
③ 仍启动期 SIGKILL → ★root 内存 dump 零注入（不触发反 Frida，项目脱壳/脱密正解）
④ 需在线 hook → ZygiskFrida（zygote 注入，§3.3，实证攻破爱加密全链路可 hook）
⑤ 到 ART 完整性级（XHS libtiny/libxyass，Java.perform 触发 SEGV_ACCERR）→ 放弃 Frida → 纯协议
```

| 触发条件 | 一线 | 兜底 |
|---------|------|------|
| 启动期 SIGKILL / raw-svc watchdog（爱加密级，spawn+attach 都死） | ① ZygiskFrida（zygote 零启动期注入） ② **root 内存 dump 零注入** | 仍不行 → 纯协议 |
| spawn 也秒退、报 `SEGV_ACCERR`（ART 代码完整性，`Java.perform` 触发） | undetected-frida + maps 抹除 | **ART 完整性级（XHS）→ 放弃 Frida** |
| 代理检测 / 配证书没网 | **ecapture（eBPF 内核 TLS 抓明文，不走代理不碰证书）** | IDA 定位 SSL_read/write + native hook |
| Frida 全军覆没 | 转**纯静态**：IDA + jadx + mitmproxy 抓包 | root 内存 dump / 纯协议 |

> 🔑 root 内存 dump 零注入 = 项目对硬壳的通用正解：App 裸启动存活 → 正常触发目标（token/加密）→ `dd /proc/pid/mem` dump 目标 SO 内存 → 静态分析/扫密钥结构。不注入 = 不触发任何反 Frida。

## 3.7 免杀工具链（待重配置路径）

| 工具 | 能力 | 具体资产 |
|------|------|---------|
| ZygiskFrida | **默认硬壳注入**：Zygisk zygote 注入 gadget，规避 ptrace/反篡改/启动 watchdog | `/data/adb/modules/zygiskfrida` v1.9.0，gadget 17.4.0 QJS |
| 魔改 new-server | strongR+Florida 全补丁，改名过进程扫描 | 已清理（2026-08-10）；如需自编译部署 `/data/local/tmp/new-server`，改名 `sysmon_svc` + root 裸启动 |
| undetected-frida (Furtif) | strongR+Florida 全补丁，Magisk/KSU 模块 | — |
| Florida (Ylarod) | 基础免杀：重命名内存池/memfd/JIT cache | **当前主力**：官方预编译 16.5.9，本地 `android_mcp\toolchain\device\frida\florida\florida-server`；设备 `/data/local/tmp/florida-server`（改名 `sysmon_helper` 过进程名扫描，§3.4） |
| strongR-frida | 字符串/pipe/agent/线程全套混淆 | — |
| TInjector | 劫持 Zygote 在 APP 启动前注入 | — |

---

# §4 SSL Pinning 8 方案选择器

```
SSL Pinning 强度
├─ 弱/无 → Reqable + TrustMeAlready
├─ 中(标准 OkHttp/TrustManager) → objection sslpinning disable / JustTrustMe(LSPosed)
├─ 强(XHS级，系统代理绕行) → mitmproxy 透明 + iptables REDIRECT
├─ Flutter(BoringSSL in libflutter) → Frida hook ssl_session_verify_cert_chain / frida4burp / 内存patch
├─ 自研 TLS(libtnet/静态 BoringSSL) → ecapture(eBPF, 无需CA, 内核抓明文) / IDA 定位 SSL_read/write + Native Hook
├─ ANet/QUIC(阿里系) → Hook libxquic xqc_h3_request_send_headers/send_body（见 android-recon §3.4）
└─ Android14+ /apex 只读证书 → MoveCertificate + OverlayFS / Magisk 注入
├─ 抖音 TTNet → eCapture text --hex 零注入（pcap 模式因魔改 boringssl 偏移常 auth-tag mismatch）
└─ Android14+ /apex 只读证书 → MoveCertificate + OverlayFS / Magisk 注入（真路径 `/apex/com.android.conscrypt/cacerts/`）
```

| 方案 | CA | Root | Flutter | A14+ | 复杂度 |
|------|:--:|:----:|:-------:|:----:|:------:|
| Reqable+TM | ✅ | ❌ | ❌ | ⚠️ | 🟢 |
| objection | ✅ | ✅ | ❌ | ✅ | 🟢 |
| mitmproxy 透明 | ✅ | ✅ | ✅ | ✅ | 🟡 |
| frida4burp | ✅ | ✅ | ✅ | ✅ | 🟢 |
| Frida native hook | ✅ | ✅ | ✅ | ✅ | 🟡 |
| **ecapture(eBPF)** | **❌** | ✅ | ✅ | ✅ | 🔴 |
| Patched APK | ✅ | ❌ | ✅ | ✅ | 🟢 |

```bash
# ecapture：内核层抓 TLS 明文，不需 CA（Android10+/Kernel5.5+）；绕代理检测（ct_client 配证书没网的正解）
adb shell su -c "/data/local/tmp/ecapture tls -m text -p <PID>"
```

---

# §5 SO 动态分析

🔴 **CHECKPOINT：CFF/虚拟化加固的 SO，禁止 `Interceptor.attach` 改代码页，必须用 Stalker trace 或运行期快照。**

| 触发条件 | 一线 | 兜底 |
|---------|------|------|
| attach 到 CFF 代码页后闪退 | 改 **Stalker** 指令级 trace（不改原代码页） | — |
| Stalker 地址配 Unicorn/hook 对不上 | Stalker 偏移有固定偏差（曾观测 +0x79），**一律以 IDA/objdump 静态绝对地址为准** | IDA 反汇编核对 |
| RDTSC/anti-tamper 时序检测 | CFF 的 RDTSC 多为 `TSC%N` 确定性计算（Apple 单站点 `TSC%3`），**注入正确值/暴力枚举 mod-N** | trace+replay 正确 dispatch |
| 符号全 strip | IDA + 动态 Hook + ida-pro-mcp AI 辅助 | r2frida 动态 |
| 模拟器偏移全错 | **arch-mismatch**：模拟器可能加载不同 ABI（Apple Music MuMu 加载 x86_64 非 arm64-v8a，偏移全不同）→ 先确认进程实际映射哪个 `lib/<abi>/` | — |

## 5.1 D-810 CFF 反混淆（IDA Pro 插件）

`plugins\d810\` → Pseudocode 窗口 `Ctrl+Shift+D` → 选 Control Flow unflatten 规则。

```
模块（optimizers/microcode/flow/flattening/）：
  unflattener.py            OLLVM
  unflattener_indirect.py   BR X8/X11 间接跳转
  unflattener_switch_case.py / unflattener_hodur.py / unflattener_fake_jump.py
dispatcher_detection.py：6 策略（HIGH_FAN_IN / STATE_COMPARISON>0x10000 / LOOP_HEADER /
  PREDECESSOR_UNIFORMITY / CONSTANT_FREQUENCY / BACK_EDGE）
适用：OLLVM / BR_X11 / Hodur / Tigress
```

> ⚠️ **LIMITS**：D-810 对**自定义分布式代码虚拟化**失败（Apple FairPlay SAP：handler 碎片在函数外、table 驱动、stack-address-keyed 状态），对 **`MOV PC,Rx` 间接跳转** flattening 也无效（XHS 实测）→ 退 runtime 快照+Unicorn 或 Frida RPC oracle。
> 跨函数不透明尾调用（`sub_X()+52; BR X1`）`default.json` 不内联 → 换 `default_indirect_resolution` / `identity_call` 或动态 trace。

**无 UI 激活**（ida-pro-mcp `py_eval`，不必 Ctrl+Shift+D）：

```python
import gc, importlib, pkgutil
st = [o for o in gc.get_objects() if type(o).__name__ == "D810State"][0]
# 打包 bug：不 walk 则 InstructionOptimizer.registry 空 → KeyError chainoptimizer
import d810.optimizers as O
for mi in pkgutil.walk_packages(O.__path__, O.__name__ + "."):
    try: importlib.import_module(mi.name)
    except Exception: pass
st.load_project("default.json")   # 或 default_unflattening_ollvm / default_indirect_resolution
st.start_d810()
# 看效果必须清缓存：ida_hexrays.mark_cfunc_dirty(ea) 再 decompile
```

## 5.2 Unicorn 运行期快照（CFF/opaque-token SO 的离线复算）

```
1) runtime mem-dump hook：dump 3 段 + 全部触及堆 + sign I/O → runtime_snapshot.json
   （Apple v9：1.8MB / 203 heap regions）
2) ★ .data.rel.ro 要在重定位之后 dump（用固定指针，不读文件）
3) dumped session/blob 含运行时指针 → 调目标函数前重定位进 Unicorn 映射
```

> **opaque-token 不可 deref**：非规范地址的 handle（Apple SAP RDI=0x1f2a04f6aec30 x86_64）且跨调用恒定 = CFF lookup table 的 opaque token，不是指针（Frida deref 抛 access violation）。含义：只模拟 sign 函数不够，lookup table 在 init+exchange 时构建 → 必须快照 CFF .bss/.data 运行时态，或模拟完整 init+exchange+sign 链。

## 5.3 send()-based 二进制 dump

设备侧 FileWriter 是瓶颈时（大/二进制 SAP/session/heap blob、权限），用 Frida `send()` 流式传到 host receiver，不在设备落盘（Apple SAP dump 死锁正是 send() 破的 → 拿到 3 组完整 SAP 会话）。任何要落盘的二进制 dump 都优先 send()/RPC。

**Hook 入口模板**：
```javascript
var addr = Process.findModuleByName("libtarget.so").findExportByName("JNI_OnLoad");
Interceptor.attach(addr, { onEnter: function(args){ console.log("[+] JNI_OnLoad JavaVM:", args[0]); }});
```

> 无 IDA Pro 时用 Ghidra；r2frida 把 radare2 接到运行中进程。
> 🔁 SO 算法要**还原成离线纯算/frozen blob** → 转 **protocol-signature-reverser**。

---

# §6 注册级完整性检测清单（reusable 6 层审计）

注册/登录页硬失败时，按层排查（Apple Music 实证，注册页强制 `isIntegrityVerificationNeeded=true`）：

| 层 | 检测 | 绕过 |
|----|------|------|
| L1 | Root/模拟器 Java 检查（`Build.PRODUCT/HARDWARE`/test-keys、`/system/xbin/su`、bitmask bit0=emu/bit1=root/bit2=debugger） | hook 这几个方法返回干净值 |
| L2 | Google Play Services 可用性（≥12451000） | hook → 可用 |
| L3 | Play Integrity API（prepareIntegrityToken；token 在全局 volatile） | hook `getIsIntegrityVerificationNeeded()`→false，或供真 token |
| L4 | **服务端 token 校验（Google 签名，不可伪造）** | root/emu/区域被拒 → 需**真机/认证设备**的 token |
| L5 | WebView JS-bridge 指纹（telephony/carrier/store-platform） | hook bridge |
| L6 | 网络签名（X-Apple-ActionSignature SAP + AMD/Anisette） | 见 protocol skill |

> 🔴 关键：注册页强制 L3/L4 → **L1 hook 救不了模拟器**（服务端要 Google 签名的真 token）。L4 不可伪造时，模拟器注册止损。

---

# 🚫 反例黑名单

1. `Interceptor.attach` 到 CFF/虚拟化代码页 → 闪退（用 Stalker / 运行期快照）
2. 用 Stalker 报告地址直接配 Unicorn/hook → 错位（以 IDA 静态绝对地址为准）
3. Root bypass 漏 `fopen` → 仍被检测（4 个文件函数全 Hook）
4. 硬壳/反 ptrace App 用 **attach** → 不是 App 死而是 **frida-server 崩**（"closed"），误判为环境问题（一律 spawn / ZygiskFrida）
5. Frida 17.x 用 `===`/`let`/箭头函数 → 脚本不加载（降 ES5）；17.x 在硬目标本身就秒退
6. 爱加密级死磕「放弃 Frida」→ 错（先 ZygiskFrida/root-dump）；ART 完整性级（XHS）才真放弃
7. L2 只靠 100ms 竞速清 maps → 18% watchdog 抢先扫会输（首选 maps 抹除）
8. XHS libtiny/libxyass 做 Frida Hook（已验证 7 种模式全败，仅调内置 API）
9. Ele.me 用 `Java.use().implementation`（quicksparrow `mthook_sign_maps` 检测，仅 Native Hook）
10. 阿里系核心流量做 OkHttp Hook（走 ANet 内部 BoringSSL，hook 不到）
11. Flutter 用 Java 层 Hook（走原生 libflutter.so）
12. 算法助手 v2.1.2 在 Android 14（"系统服务未启动" 不兼容）
13. D810-ng 指望搞定 `MOV PC,Rx` 间接跳转 CFF（无效，转快照/RPC）
14. 高频协议请求不限频 → 风控/封号（风控观察 ON 时记）
15. 真机 arm64 new-server 与 MuMu x86_64 交叉推送
16. 美团/猫眼按包名 spawn；Keeta 连续注入过期/无效 mtgsig（设备软封 #41SR，原版 App 也 403）
17. 绕过 MCP 手写 `/data/system/junge/<pkg>/`（会留 root:root 污染；MCP 已自动 owner=system:system，直接用工具即可）
18. 平安/360VIP 上再试 ZygiskFrida / 留 new-server（崩 zygote 或持久 SIGSEGV）

---

# 故障排查

| 问题 | 原因 | 解决 |
|------|------|------|
| `frida-ps` 无输出 | server 未启/未转发/版本不配 | 起 frida-server + `adb forward tcp:27042 tcp:27042` + 客户端 16.5.x |
| `get_process(pkg)` 报 ProcessNotFoundError 但 adb 看到进程 | **App 反枚举**（dy 抖音 MS SDK 275208 反检测监控区运行一段时间后从 frida 进程表隐藏） | `adb shell pidof <pkg>` 拿 pid → `dev.attach(pid)` 直连（SF-016） |
| frida 16.5.7 RPC `exports_sync` 报 `unable to find method 'xxx'` | Python 绑定把方法名 **lower() 后查找**（camelCase/snake_case 全报错） | JS 端 rpc.exports 方法名一律**全小写**（`oraclebatch`/`getbase`） |
| 脚本不加载 | 17.x 语法/API | ES5 写法 + `Process.findModuleByName` |
| attach 报 "closed" / frida-server 崩 | 反 ptrace 壳（爱加密）| 改 spawn / ZygiskFrida / root dump（§3.4/3.6） |
| spawn 秒退 SEGV_ACCERR | ART 完整性检测 | undetected-frida + maps 抹除；仍不行→放弃 Frida |
| hook 装上但 App 静默不出数据 | quicksparrow ART-hook 检测服务端封 | 仅 Native Hook（§3.5） |
| 抓包无明文 | SSL Pinning | §4 选择器；代理检测→ecapture |
| `TransportError` / 17.x 连不上 | 客户端与 new-server 16.5.8 不配 | `.venv-frida-16.5.7` + adb forward + add_remote_device |
| 算法助手配置写了不生效/崩 | root:root（旧数据/绕过 MCP 手写） | MCP 现自动 system:system；存量残留 `chown -R system:system /data/system/junge/<pkg>` 或清目录重写 |


---
name: android-dynamic
description: Android 动态调试专项。负责运行期 Frida Hook、Frida 版本兼容（含真机 arm64≠MuMu x86_64）、反 Frida 三层检测对抗（Zygisk 默认注入向量 / maps 抹除 / root 内存 dump 零注入逃生门）、spawn-vs-attach（含美团系 attach 例外）、商业加固 hook 层规则（quicksparrow/ANet/360VIP）、Root 检测绕过、SSL Pinning 8 方案选择器、SO 分析（IDA/Stalker/Unicorn 快照/RDTSC/D-810 CFF 含无 UI 激活）、注册级完整性检测清单。内含 APP 安全等级矩阵与「及时止损线」。
whenToUse: 用户提到 Frida、Hook、动态调试、frida检测、反检测、注入秒退、attach崩server、ZygiskFrida、spawn注入、SSL pinning、抓包绕过、SO分析、Stalker、Unicorn、RDTSC、D-810、CFF、native hook、quicksparrow、objection、Florida、ecapture、完整性检测。
---

# Android Dynamic — 动态调试 / Frida 对抗 / SSL / SO

## 任务与边界

本 Skill 负责 Android 运行期证据：Hook、trace、RPC、SSL/native 网络观察和反注入判因。

> 🔴 **边界**：
> - 反编译/提取 API静态侦查/抓包通/akp/组件 → **android-recon**
> - 取真实 DEX、VDEX、内存 SO 短提取（脱密） → **android-unpack**
> - Unicorn/unidbg、frozen blob、算子提升和离线协议实现 → **protocol-signature-reverser**（本 skill 只负责动态定位/trace/RPC，不做纯算实现）

> ⏺️ **全程风控记录**：风控记录开关 YES 时（AGENTS.md），本 skill 执行全程遇到的风控素材随手记到 `projects/<target>/docs/risk-observations.md`——反 Frida/Root/Hook 检测命中面/spawn-attach 存活/静默封 API/高频封号 + 任何不起眼但对风控对抗有用的点（格式见黑名单 19）。

```
🛑 动 Hook 前先过三关：① APP 在安全等级矩阵第几级？② 检测 Frida 吗？③ 选对注入链与绕过方案
```

> ADB 统一 bundled `android_mcp\toolchain\bin\windows\platform-tools\adb.exe`。真机基线 **Pixel 4 / 9C181EC3BF7E0D / Android 10 arm64 / Magisk + Zygisk**。

> 🧰 **配套 MCP（无 UI 优先，工作流见 [AGENTS.md]）** 
—— 本 skill = 工作流**阶段 4（动态验证）**，优先用自建 `frida_orchestrator` 而非截图点按：
> - 魔改frida-server 生命周期（MCP 主力管魔改 `/data/local/tmp/florida-server`；官方 f1657 回退；改名裸启动 §3.4）：`start_patched_frida_server` / `patched_frida_status` / `stop_patched_frida_server`；进程枚举 `frida_ps`。
> - 算法 oracle：`generate_frida_rpc_template` + `frida_rpc_call`（把目标函数当在线 oracle 验证）。
> - 无 UI 注入比对：算法助手 `algorithm_aide_*`、LSPosed `lsposed_set_scope`/`lsposed_set_module_enabled`。
> - SO 深度分析仍用 `ida-pro-mcp`（IDA 内 Ctrl+Alt+M 启动）。
> - **native SO 套件（本机 `tools\so-reverse\`，分工详见 [AGENTS.md]**：重度反编译/去混淆**首选 IDA Pro**；二线 Ghidra `ghidraRun.bat`（需 Java 17）；radare2 `rabin2` 快速体检；QBDI `qbdi\local\bin\qbdi-template-AARCH64`（真机 arm64）动态插桩。**全套已就位**。
> - 输出落 `projects/<target>/hooks/` 与 `artifacts/`，保留脚本、日志、时间、版本、PID、模块基址和清理结果。

---

## 证据门

“有反 Frida/反调试”必须同时具备：

1. 同一 serial、ABI、client/server 和 transport 能对已知无防护 App 完成相同 attach/spawn；
2. 目标失败可稳定复现，并有 logcat/tombstone/进程或 server 状态证据。

没有两证时只报告工具链症状，不升级结论。注入、代理或进程连续出现三次同类失败时停止同类尝试，进入归因或零注入路径。
> 弹窗让用户选择用哪个工作流
> 工作流2在 `android-dynamic/references/way_two.md §7 工作流2（归因/零注入）`，工作流1在 `android-dynamic/SKILL.md §8 工作流1（默认工作流、现场分析）`。
# 工作流1（默认工作流、现场分析）
### 1. 定义最窄运行边界

从静态调用链选择离信任变化最近且侵入最小的位置：

1. request builder / signer 的输入输出；
2. Java↔JNI marshaling；
3. crypto 原语入参；
4. native 网络明文入口；
5. 只有上层不可达时才 trace 更底层代码。

不要先做广域 Hook。记录“为什么这个点能区分当前两个假设”，先观察，再决定是否修改返回值。

### 2. 设备与状态预检

写入/注入前记录：

- serial/state/ABI、包名、PID 和前台 App；
- server/client 版本与监听地址；
- Zygisk/LSPosed/AlgorithmAide/HMA 当前状态；
- 全局 proxy、NAT、ADB forward；
- 对应恢复命令。

设备歧义、offline、ABI/版本不配、包名不合法、前一次注入残留或恢复路径不明确时停止。动态工作结束后，前台 App、proxy/NAT、forward 和模块配置应恢复到基线。

### 3. 选择注入方式

侵入度按缺口选择，不按固定流水线升级：

| 已有证据 | 入口 | 失败后 |
|---|---|---|
| 不需进程内证据 | eCapture/Root 读取/原版流量 | 保持零注入 |
| 目标已运行且 attach 可用 | 精确 PID attach | 核对 tombstone/server，再决定是否 spawn |
| 必须捕获冷启动初始化 | spawn | 启动期 watchdog 则停止重复 spawn |
| 已证实 ptrace/启动期检测且在线 Hook 必需 | 评估 Zygisk/Gadget | 系统/zygote 异常立即恢复并降为零注入 |
| ART 完整性或进程级反注入 | 不做 Java/进程内 Hook | Root dump/eCapture/纯协议 |

已知局部经验只能作为候选：商业 ART-hook 检测目标优先 native；部分美团系使用运行中 PID attach；抽取壳的冷启动/执行覆盖由 `android-unpack` 决定。每个新版本必须重新用证据确认。

### 4. Hook 与 RPC

优先 `start_frida_hook` 或 `generate_frida_rpc_template` + `frida_rpc_call`。脚本以当前 16.5.x runtime 可解析的 API 为准：

```javascript
Java.perform(function () {
  var Target = Java.use("com.example.Target");
  Target.sign.implementation = function (input) {
    var out = this.sign(input);
    send({kind: "sign", input: String(input), output: String(out)});
    return out;
  };
});

var libc = Process.findModuleByName("libc.so");
var fopen = libc ? libc.findExportByName("fopen") : null;
if (fopen) {
  Interceptor.attach(fopen, {
    onEnter: function (args) { send({kind: "fopen", path: args[0].readUtf8String()}); }
  });
}
```

- 二进制大数据分块 `send()` 或写临时文件后 `root_pull_file`；每块带 offset/total/hash。
- 模块后加载时监听加载事件后 re-arm；不能只在 spawn 时查一次基址。
- 动态注册 JNI 用 `register_natives` 模板逐项记录 method name、JNI signature、function pointer、module+offset；表数量必须有上限，空指针/坏指针逐项报错，不能因一项不可读中断整次映射。
- Native 地址一律记录 module hash、base 与 relative offset，不只保存绝对 VA。
- RPC 是 oracle 依赖；交付必须明示设备/进程/session 条件。

### 5. Java/ART 与 native 网络栈

| 现象 | 处理 |
|---|---|
| Java Hook 装上但业务静默降级 | 先撤 Hook 做原版对照；若证实 ART-hook 检测，改 JNI/native 边界 |
| Cronet/TTNet | 不继续堆 OkHttp Hook；定位 native request/crypto/TLS 边界 |
| ANet/libtnet/libxquic | Hook 实际 header/body 提交点；模块后加载需 re-arm |
| Flutter/libflutter | 从 native TLS/serializer/JNI 边界观察 |
| Shark/NV/私有隧道 | 先确认隧道入口和传输层；签名归因转 protocol |

Hook 命中只证明代码执行；必须把输入、输出、调用栈或服务端分支与同一会话对应起来。

### 6. SSL/抓包选择

按最低侵入度选择：

- 标准信任链/弱 pinning：Reqable/Charles + 正确 Android 14 CA；
- 标准 Java pinning：在当前 App 范围内观察/绕过 TrustManager/OkHttp；
- native TLS、代理检测或 App 配代理即断网：eCapture 或目标 native 明文入口；
- QUIC/私有传输：定位 header/body 提交点，传输指纹问题交 `projects/fp_stack/`；
- 透明代理/iptables 只在需要时使用，写前保存规则，结束精确恢复。

是否抓到包不等于签名通过；HTTP 200 不等于业务成功。

### 7. SO 运行期分析

静态地址与函数范围先由 IDA/rabin2/Ghidra headless 确认。GhidraMCP 当前仅 `documented`，未注册、未 validated。

- 代码页 Hook 导致完整性失败：停止改页，使用 Stalker、硬件/Root 取证或运行期快照；
- trace 地址必须换算为 module+offset，并与静态反汇编核对；
- 检查 `RDTSC/RDTSCP/CNTVCT_EL0/gettimeofday/clock_gettime` 等时序源；
- 快照保存映射、重定位后只读段、堆依赖、输入输出与版本锚点；
- 需要 Unicorn/unidbg/frozen blob 或纯算时转 `protocol-signature-reverser`。

## 失败分支

| 触发 | 一线处理 | 仍失败 |
|---|---|---|
| `frida_ps` 空/TransportError | 核 server、loopback forward、client/server 版本 | 重启 MCP/server，不切 PATH CLI |
| attach 报 closed/server 崩 | 核 PID、root、tombstone 与无防护对照 | 需要冷启动才试一次 spawn；否则零注入 |
| spawn 启动期 SIGKILL | 保存 logcat/tombstone，判 watchdog | 不循环换版本；Root dump/eCapture |
| Java Hook 成功但业务失效 | 撤 Hook 做原版同环境对照 | 改 JNI/native，保留判因证据 |
| native Hook 一装就崩 | 核地址/ABI/模块 hash/代码完整性 | Stalker/快照/零注入 |
| RPC 输出可得但自建请求失败 | 固定同一会话做传输/字段 diff | 转 protocol 做签名/生命周期判因 |

## 交付门

至少保存 3 组非样例输入→输出、脚本/hash、设备与 App 版本、session/PID、模块 offset、原版对照、清理结果和未解项。若只实现 RPC/oracle，明确标为止损型或在线依赖，不得称离线纯算。

## 不要做

1. 不把 Zygisk、spawn 或广域 Hook 当默认第一步。
2. 不混用 arm64 真机与 x86_64 模拟器二进制，不混用 16.5.x server 与 PATH 17.x 客户端。
3. 不按包名盲杀、不复用旧 PID、不用 `pkill -f` 代替身份核验。
4. 不在未自证工具链时宣称“目标有反 Frida”。
5. 不把 Hook 安装成功、日志出现、HTTP 200 或可解析输出当最终验收。
6. 不在本 Skill 中把 trace/快照包装成离线算法完成。




## 参考资料（references/，按需加载）

| 文件 | 内容 | 何时读 |
|------|------|--------|
| [references/frida-basics.md](references/frida-basics.md) | §1 版本矩阵、17.x API 差异、spawn/attach 命令、Hook 模板 | 写 Frida 脚本前、版本对齐 |
| [references/anti-detection.md](references/anti-detection.md) | §3 Root/反 Frida 三层、ZygiskFrida、spawn 规则、加固 hook 层、止损阶梯、免杀链 | 定完安全等级后选注入/绕过打法 |
| [references/ssl-pinning.md](references/ssl-pinning.md) | §4 SSL Pinning 8 方案分支与对比、ecapture | 抓不到明文、选 SSL 绕过方案 |
| [references/so-dynamic-analysis.md](references/so-dynamic-analysis.md) | §5 D-810/Unicorn 快照/send dump、§6 完整性 6 层 | CFF/SO 动态分析、注册完整性审计 |

# 工作流2 （结合经验固定套路应对）
## §1 Frida 版本兼容 + 真机基线（写脚本前必读）

> 完整版本矩阵、17.x API 差异修复表、spawn/attach 命令、Java/Native Hook 模板见 **[references/frida-basics.md](references/frida-basics.md)**。

🔴 **CHECKPOINT：写任何 Frida 脚本前确认 frida-server 版本与引擎。** 主力 florida-server 16.5.9 / 回退 f1657 16.5.7，客户端统一 `.venv-frida-16.5.7`（**16.5.x↔16.5.x**）；16.7.19 仅普通目标。🔴 **17.x 在硬目标全挂**（XHS 秒退），且 17.9.1+ 移除 `Module.findExportByName`、Duktape 须降 ES5（`var`/`==`/普通 `for`）。硬壳默认 **spawn**（`-f`，bypass 在初始化前生效），命令与模板见 frida-basics.md。

---

## §2 APP 安全等级矩阵 + 注入决策

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

## §3 反检测对抗

> Root 绕过、反 Frida 三层模型、ZygiskFrida 完整配置、spawn-not-attach、商业加固 hook 层规则、止损阶梯、免杀工具链**全部细节**见 **[references/anti-detection.md](references/anti-detection.md)**。下面是每节核心结论与锚点。

### 3.1 Root 检测绕过（4 层缺一不可，必须 spawn）

Native 文件检测（`faccessat/access/stat/fopen`，**`fopen` 不能漏**，拦 su/magisk 路径）+ Java 层（RootBeer/isRooted 返回 false）+ GPS/模拟器 + WebView/完整性，四层都要盖。详见 anti-detection.md §3.1。

### 3.2 反 Frida 三层模型 + 绕过

L1 进程/cmdline → 重命名+Zygisk；**L2 内存签名 → maps 抹除（首选，无可扫之物），100ms 竞速只是降级**；L3 ptrace → Zygisk 结构性免疫或伪造 TRACEME。三层表与代码见 anti-detection.md §3.2。

### 3.3 ZygiskFrida 默认注入（爱加密级 RASP 实证攻破）

zygote 注入 gadget、不走 ptrace、App 代码前就位。模块 `/data/adb/modules/zygiskfrida` v1.9.0，gadget 17.4.0 QJS（**无 Java 桥只 native hook**），`on_load=resume` + `start_up_delay_ms=20000`，重启等 ~35s attach "Gadget"。`re.zyg.fri` 被 relabel 时 `chcon u:object_r:shell_data_file:s0` 修。完整配置见 anti-detection.md §3.3。

### 3.4 spawn-not-attach 硬规则 + 重命名（硬壳必读）

**硬壳/反调试一律 spawn 不 attach**（爱加密实测 attach 直接崩 frida-server 本体）。**例外：美团系（Keeta/猫眼）用 attach pid**，MTGuard 对 spawn 更敏感。壳扫进程名杀 frida/florida/server → 改名 `sysmon_svc`/`sysmon_helper` 后 **root 裸启动**存活。详见 anti-detection.md §3.4。

### 3.5 商业加固 hook 层规则（quicksparrow / ANet）

quicksparrow `mthook_sign_maps`（Ele.me）扫 ART hook 签名 → 服务端**静默封 API**（hook 装上但不出数据）→ **仅 Native Hook，不碰 Java/ART**；ANet/`libtnet.so`（阿里）OkHttp hook 无效，native libssl hook 不触发 quicksparrow 值得做。360VIP live 拒绝一切进程内注入，只许 Root dump。MCP 已自动处理算法助手 system:system 属主。详见 anti-detection.md §3.5。

### 3.6 及时止损线 + anti-RASP 阶梯（最重要的判断）

🔴 **注入即秒退先判检测层级：爱加密级 ≠ 放弃 Frida，ART 完整性级（XHS，Java.perform 触发 SEGV_ACCERR）才真放弃。** 阶梯：①改名+root 运行 ②spawn ③仍 SIGKILL→root 内存 dump 零注入（硬壳通用正解）④需在线 hook→ZygiskFrida ⑤ART 完整性→纯协议。完整阶梯与兜底表见 anti-detection.md §3.6。

### 3.7 免杀工具链

默认硬壳注入 = ZygiskFrida；当前主力免杀 server = Florida 16.5.9（改名裸启动）；strongR/undetected-frida/TInjector 备选。工具-能力-资产对照表见 anti-detection.md §3.7。

---

## §4 SSL Pinning 8 方案选择器

> 完整 8 方案分支图、各方案 CA/Root/Flutter/A14/复杂度对比表、ecapture 命令见 **[references/ssl-pinning.md](references/ssl-pinning.md)**。

分流：弱/无→Reqable+TMA；标准 OkHttp→objection/JustTrustMe；强(XHS)→mitmproxy 透明+iptables REDIRECT；Flutter→hook BoringSSL/frida4burp；自研 TLS(libtnet)/代理检测/抖音→**ecapture(eBPF，无需 CA，内核抓明文)**；ANet/QUIC→Hook libxquic（android-recon §3.4）；A14+ /apex 只读证书→MoveCertificate/OverlayFS。

```bash
adb shell su -c "/data/local/tmp/ecapture tls -m text -p <PID>"   # 内核抓 TLS 明文，不需 CA
```

---

## §5 SO 动态分析

> D-810 CFF 反混淆（含无 UI 激活代码）、Unicorn 运行期快照、send() 二进制 dump、opaque-token 判读全部细节见 **[references/so-dynamic-analysis.md](references/so-dynamic-analysis.md)**。

🔴 **CHECKPOINT：CFF/虚拟化加固的 SO，禁止 `Interceptor.attach` 改代码页，必须用 Stalker trace 或运行期快照。**

- attach CFF 代码页闪退 → **Stalker 指令级 trace**；Stalker 地址有固定偏差，**一律以 IDA 静态绝对地址为准**。
- RDTSC 时序检测多为 `TSC%N` 确定性计算 → 注入正确值/暴力枚举 mod-N。
- 模拟器偏移全错先查 **arch-mismatch**（进程实际加载哪个 `lib/<abi>/`，真机 arm64 ≠ MuMu x86_64）。

### 5.1 D-810 CFF 反混淆（IDA Pro 插件）

`plugins\d810\` → Pseudocode 窗口 `Ctrl+Shift+D` 选 unflatten 规则，适用 OLLVM/BR_X11/Hodur/Tigress；无 UI 用 ida-pro-mcp `py_eval` 激活（须 walk_packages 否则 registry 空）。**LIMITS：自定义分布式虚拟化（Apple SAP）与 `MOV PC,Rx` 间接跳转无效 → 退运行期快照/RPC**。代码与模块清单见 so-dynamic-analysis.md §5.1。

### 5.2 Unicorn 运行期快照

CFF/opaque-token SO 离线复算：dump 3 段+触及堆+sign I/O，**.data.rel.ro 要在重定位之后 dump**，运行时指针调前重定位进 Unicorn。非规范地址且跨调用恒定的 handle = opaque token（不可 deref），须快照 .bss/.data 运行时态或模拟完整 init+exchange+sign 链。详见 so-dynamic-analysis.md §5.2。

### 5.3 send()-based 二进制 dump

大/二进制 dump 优先 Frida `send()` 流式传 host，不在设备落盘（Apple SAP dump 死锁正是 send() 破的）。Hook 模板见 so-dynamic-analysis.md §5.3。

> 🔁 SO 算法要**还原成离线纯算/frozen blob** → 转 **protocol-signature-reverser**。

---

## §6 注册级完整性检测清单（reusable 6 层审计）

注册/登录页硬失败按 L1 Root/模拟器 Java → L2 GMS 可用性 → L3 Play Integrity API → **L4 服务端 token 校验（Google 签名不可伪造）** → L5 WebView JS-bridge → L6 网络签名 逐层排查。🔴 注册页强制 L3/L4 时 **L1 hook 救不了模拟器**，L4 不可伪造则模拟器注册止损。六层绕过表见 so-dynamic-analysis.md §6。

---

## 🚫 反例黑名单

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
14. 高频协议请求不限频 → 风控/封号
15. 真机 arm64 new-server 与 MuMu x86_64 交叉推送
16. 美团/猫眼按包名 spawn；Keeta 连续注入过期/无效 mtgsig（设备软封 #41SR，原版 App 也 403）
17. 绕过 MCP 手写 `/data/system/junge/<pkg>/`（会留 root:root 污染；MCP 已自动 owner=system:system，直接用工具即可）
18. 平安/360VIP 上再试 ZygiskFrida / 留 new-server（崩 zygote 或持久 SIGSEGV）
19. 风控记录 YES（AGENTS.md 两开关）时，把反检测命中/封号/环境检测触发记到 `projects/<target>/docs/risk-observations.md`：开关二 YES → 按 E-/F- 动态条目模板记完整条目；仅开关一 YES → 记一行；均 NO → 不记

---

> 📝 **记录前**：风控记录 YES 时，把 Hook/对抗中实测到的**环境检测与封禁信号**记到 `projects/<target>/docs/risk-observations.md`：反 Frida/Root/Hook 检测命中面、spawn/attach 存活差异、hook 装上但静默封 API、高频请求触发封号；**以及清单外任何你认为对抗风控可能用得上的点（哪怕不起眼）**（格式见黑名单 19）。

## 故障排查

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

---
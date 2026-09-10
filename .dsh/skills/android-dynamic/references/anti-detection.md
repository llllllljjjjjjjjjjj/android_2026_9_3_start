# 反检测对抗（详细手册）

> 本文件由 `SKILL.md §3 反检测对抗` 引用，属于**按需加载**层：Root 绕过、反 Frida 三层模型、ZygiskFrida 注入、spawn-not-attach、商业加固 hook 层规则、止损阶梯、免杀工具链时读。先在 SKILL.md §2 安全等级矩阵定级，再到本文件找对应打法。

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

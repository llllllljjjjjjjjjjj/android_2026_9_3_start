# unidbg 补环境（SO 离线模拟完整手册）

> 本文件由 `SKILL.md Phase 6：unidbg 补环境` 引用，属于**按需加载**层：SO 离线跑出签名、补 JNI/文件/属性/时间环境、jar 化工程化交付时读。注意：生命周期绑定/会话态（SF-013）unidbg 同 SO 也被拒，优先在线 oracle，不投入补环境。

---

## Phase 6：unidbg 补环境（SO 离线模拟）

> 当策略选 D/E（虚拟化/反模拟）受阻、又想脱离设备时，用 unidbg 让 SO 离线跑出签名。（H 的 VMP+轮换是纯算死路，unidbg 同样难产——优先在线 oracle，不投入补环境。）

```
环境：JDK 17 + Maven（JDK 21 与 unidbg 有 Module 类名冲突）
流程：编译 unidbg → 加载目标 so → 验证 JNI_OnLoad/RegisterNatives → 调签名方法 → 按崩溃点补环境
```

| 触发条件 | 一线修复 | 兜底 |
|---------|---------|------|
| unidbg 编译报 Module 类冲突 | 降 **JDK 17**（不要 JDK 21） | Maven 3.9.x 已验证可用 |
| 调签名方法返回 null | 逻辑已跑但缺环境 → 补 JNI 回调（系统属性/虚拟模块注册） | 按崩溃地址逐个补内存/系统调用 |
| x86_64 栈 dump access violation | dump 方向错（x86_64 栈向低地址增长）确认读取方向 | rdi 内存诊断法定位真实访问地址 |
| 目标 SO 依赖低版本 libc 行为（JNI_OnLoad 跑不完） | 用 **sdk23 的 libc**（ct_client 关键突破） | — |
| 反射混淆取不到 methodID | JNI 函数表 SVC 蹦床 hook：`table[7]`=FromReflectedMethod/`[8]`=FromReflectedField，拦 x1(jobject) 反射 resolve 真 id 塞 x0 | hook 必须落 SO 代码区（SVC 蹦床 0xfffe.. 不触发 UC_HOOK_CODE） |
| .bss 配置全 0（检测置 tamper 标记） | **靶向堆恢复**：dump 真机堆（带 manifest VA size 列表）→ 只填 JNI_OnLoad 后仍为 0 的槽（`if(cur!=0)continue`），heapRestore 在 callJNI_OnLoad **之后** | 保留 unidbg JNI handle 不被真机值覆盖 |
| unidbg"跑通"但密文错 | 验执行正确性（**SF-014**：CTR keystream 整条恒定=执行坏） | 转真机 root 内存 dump 取中间量 / 长度对拍 |

### 补环境三边界（决策前先判断）

| 边界 | 可行性 | 说明 |
|------|--------|------|
| **完全离线**（不联网+不设备） | ❌ 常死结 | 签名依赖服务器密钥交换的 session（如 FairPlay）离线无法凭空生成 |
| **一次性联网**（补环境跑 init+exchange 建 session） | ✅ 可行但大工程 | session 持久化后可复用，之后纯本地 |
| **Frida RPC**（设备在线） | ✅ 最快 | 零额外逆向，设备在线直接调原函数（策略 E/H） |

🔑 **关键认知**：补环境能脱离 App/设备，但**未必能脱离网络**。签名永不过期类（捕获即复用）优先走捕获复用，纯算可能是死路。

### 执行正确性红灯清单（把 SO 当 oracle 前必查，承接 SF-014）

- 固定目标 SO/hash/ABI、loader、JDK/NDK/系统库版本（**环境漂移 = 结果漂移**）；
- 证明 `JNI_OnLoad`/`RegisterNatives` 与目标调用链**真实执行**；
- 先对标准 AES/hash 或已有真机向量对拍（SF-012，≥3 组起步）再当 oracle；
- 检查时序源、系统属性、线程、文件、随机数、网络/session 与重定位数据；
- 见到 **重复 keystream / 全零状态 / 固定错误分支 / 只返回预期长度** → 标记 **invalid oracle**，补环境或废弃，不得将返回值当解。

> 补环境可以脱离 App，不自动等于脱离设备/账号/网络；对外说明初始化/session 依赖（对应交付形态见 SKILL.md 三级交付）。

### 6.1 unidbg 工程化交付：SO 参数生成逻辑 → jar → Python / MCP

> 凡是从 SO 里产出的值——**签名 / 设备指纹(fp_stack/blackBox) / 防爬 token(e9hgat5k/mtgsig/CKey)
> / 加密参数 / 密钥派生**——只要 SO 已能在 unidbg 补环境跑通，就**不重写算法**，直接 jar 化交付，
> 省去纯算重写工时与后续每次生成的 token 消耗。

🔴 **打包前置门槛（硬约束，先 Java 验证 → 再打 jar）**：
1. 在 unidbg 工程里写 `main()` 验证：加载目标 so → 跑 JNI_OnLoad/RegisterNatives → 按崩溃点补环境 → 生成参数
2. 与真机/抓包样本**字节级对拍**（SF-012：≥3 组非样例起步 / 成熟 100+；RSA/随机填充类验明文与结构）；不一致 = 补环境还没成，**禁止打 jar**
3. 验执行正确性（SF-014：CTR keystream 整条恒定 = 执行坏）→ 通不过就回到补环境
4. jar 只是封装层，不修「补环境失败」；跳过 1-3 直接打包 → JPype/MCP 层拿到全错值，更难排查

#### 补环境标准步骤

```
① 建 Java 工程继承 AbstractJni → ② new AndroidEmulator(sdk 版本)
→ ③ createDalvikVM(apk) → ④ vm.loadLibrary(so, force)
→ ⑤ module.callJNI_OnLoad(emulator, vm)   ← 关键：不跑这个，JNI 函数注册不全
→ ⑥ 定位函数（导出用 symbol；RegisterNatives 非导出 → 靠 JNIEnv 注册表/静态偏移）
→ ⑦ module.callFunction(emulator, addr, args...) → 按崩溃点补环境
```

#### 补环境经验表（每次试错追加一行，延续 Phase 6 表格）

| 触发条件 | 一线修复 | 兜底 |
|---------|---------|------|
| 编译报 `Module` 类名冲突 | **JDK 8**（boot-server 0.9.9）或 JDK 17（较新 unidbg）；禁 JDK 21 | Maven 3.9.x |
| `loadLibrary` 后找不到导出函数 / 符号表空 | 先 `callJNI_OnLoad`——多数 so 的 JNI 函数在 `JNI_OnLoad` 里 `RegisterNatives` 动态注册 | 静态定位偏移：IDA 找 `RegisterNatives` 的 methods 表地址，用地址调用 |
| 调 Java 层方法返回 null / 崩溃 | 缺 Java 环境 → 补 `vm.setJni`、`vm.setVerbose` 定位到哪个 `JNIEnv` 回调缺失 | 用 **Jnitrace** 抓真机 JNI 调用日志，照着补 |
| so 读 `System.getProperty`（如 `ro.build.fingerprint`）返回 null 崩溃 | 补系统属性：往 vm 塞对应 property | 真机 `getprop` 抄一份全量塞 |
| so 读 `/proc/self/maps`、`/system/build.prop`、`/proc/self/status` 崩溃 | 补**文件系统层**（IOResolver），文件内容保持与真机字段一致、PID 对齐 | 真机 `adb shell` 拉对应文件内容塞进 resolver |
| 时间/反模拟检测（RDTSC / clock_gettime / gettimeofday）走错分支 | 补时间实现（返回递增/固定合理值），或 hook 检测点改返回值 | SF-005：模拟前先搜 RDTSC，中招则转 Frida RPC |
| `ServiceManager.getService` 取不到服务 | 补 `ServiceManager` 的 `sCache` 静态字段（zhkl0228#452 同款） | 直接 hook 掉该服务调用，返回桩对象 |
| `JNI_OnLoad` 跑不完 / so 依赖低版本 libc 行为 | 用 **sdk23 的 libc**（ct_client 关键突破） | 换 emulator sdk 版本试 |
| unidbg「跑通」但密文/参数错 | 验执行正确性（SF-014：CTR keystream 整条恒定 = 执行坏） | 转真机 root 内存 dump 取中间量 / 长度对拍 |
| 多线程 so（pthread 建线程）崩溃 / 结果错 | 单线程调（boot-server 默认禁多线程；MCP 框架已串行） | 请求方法里 new unidbg 对象 |
| so 检测「unidbg 环境特征」/ 中央仓库 0.9.9 踩 bug | 切本地 `D:\unidbg-0.9.9\unidbg-0.9.9` 源码 `mvn install` 替换（版本仍 0.9.9，自动命中） | GitHub 拉魔改版 unidbg；或自己魔改 unidbg 库抹特征（**需用户同意**） |

#### 三种交付形态（Java 验证通过后）

| 形态 | 链路 | 调用侧 | JDK |
|------|------|--------|-----|
| A jar HTTP 服务 | `tools\unidbg-boot-server\` `mvn package` → `java -jar target\unidbg-boot-server-0.0.1-SNAPSHOT.jar` 起 9999 | Python `requests` 调 HTTP | **JDK 8**（0.9.9） |
| B jar 进程内直调 | `mvn package` 产出 `*-shaded.jar`（maven-shade 打全 unidbg 依赖） | Python `jpype1` 起 JVM 进程内直调 | 0.9.9→JDK8，较新→JDK17（禁21） |
| C MCP 调用 | 同一 `*-shaded.jar` → unidbg_mcp server 内部 JPype 直调 | DSH `mcp__unidbg__generate` | 同形态 B |

#### 红线

- 🔴 禁止 Java 层未字节级验证就打 jar（jar 不修补环境失败）
- 0.9.9 老框架 JDK 8 与裸 unidbg JDK 17 两套环境不混用
- 形态 B/C fat jar 必须 shade 打全 unidbg 依赖，否则 ClassNotFoundError
- unidbg 多线程支持差：默认单线程调用（MCP 框架已串行，天然满足）
- ⚠️ 生命周期绑定/会话态参数（SF-013）离线 unidbg 同 SO 也被拒 → 不投入，转策略 G/H 在线

> 权威来源：[unidbg-boot-server README](https://github.com/anjia0532/unidbg-boot-server) / [零基础入门](https://juejin.cn/post/7025794546655035422) / [打包 jar 调用](https://blog.csdn.net/qq_41369057/article/details/131396370)；补环境实战 [52pojie 第二十四课](https://www.52pojie.cn/thread-2058523-1-10.html) / [第二十五课](https://www.52pojie.cn/thread-2063957-1-1.html)；分层笔记 [库函数层](https://cn-sec.com/archives/5195623.html) / [文件系统层](https://cn-sec.com/archives/5181371.html) / [初始化问题](https://cn-sec.com/archives/5196353.html)；[ServiceManager #452](https://github.com/zhkl0228/unidbg/issues/452)。

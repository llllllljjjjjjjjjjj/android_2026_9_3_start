# 算法还原策略选择器（证据 → 策略 → 验收）

> 本文件由 `SKILL.md Phase 3：算法还原策略选择器` 引用，属于**按需加载**层：SO 分析 + 假设验证后选 A/B/C/D/E/F/G/H/RSA 策略时读。核心是「证据 → 策略 → 验收」三列路由表；另含案例/工时参考、混淆先分类、假设连线、D vs H 判定、oracle 改造阶梯、止损决议门。

---

## 核心策略表（证据 → 策略 → 验收）

> 🔴 **CHECKPOINT**: 策略选择前必须确认: SO 搜索过标准加密常量了? Unicorn 前检查过 RDTSC? 反模拟检测评估完成? 选择策略后 🛑 **STOP** — 展示策略选择理由给用户确认，再执行。

| 证据 | 策略 | 验收 |
|---|---|---|
| 找到标准加密常量（AES S-box / SHA K表 / HMAC 魔数）、输入链清楚（SF-001） | **A** 标准库重写 | canonical bytes、key/IV/padding；最低 3 组非样例 oracle 字节级一致（成熟确定性实现追加 100+ 回归） |
| GF(2^8) 字节变换、无标准常量 | **F** IDA 反汇编 + 算子序列提取 → frozen op list | 非样例输入逐字节一致 |
| 固定执行路径依赖大 SO 只读状态（CFF 重度 + D-810 无效） | **C** Frozen Blob / 快照提取 | blob 来源、重定位、版本边界、oracle 对拍（禁止把 blob 当黑盒猜值） |
| CFF 混淆 + D-810 unflattener 有效 | **B** D-810 unflatten → 算法追踪 → 重写 | 反汇编结构复核后重写 / 提取，oracle 对拍 |
| 定制代码虚拟化 + 200+ handler + 跳转表 | **D** Frida 会话提取 → 离线签名 | 会话重放 / 离线签名稳定复现（send() 传数据破 dump 死锁） |
| 反模拟检测（RDTSC/时间，SF-005）+ SO 不复杂 | **E** Frida RPC 在线签名 | 真机 oracle 对拍；明示设备/session 依赖（止损型） |
| BCF / FLA / MBA、间接 BR/BLR、或 VM/时序反模拟 | **先分类缺口**：局部传播 / trace+快照 / Unicorn / unidbg，不直接套 CFF 系 | 反汇编边界 + 已知向量对拍，再任意输入；先查 RDTSC（SF-005） |
| RSA-PKCS1 随机填充 / 混合加密（含 rand 会话密钥，密文每次不同） | **RSA** hook 加密原语入参 → 重建结构 | 可解密/验签、字段谱系与长度；**不追密文字节**（SF-012） |
| 裸 HTTPS/QUIC 协商失败、原版同环境能通（请求未到网关） | **H** 传输复刻 `projects/fp_stack/`（真机 CH + 私有 QUIC 版本） | verbatim 请求先通，再判断签名（SF-020） |
| 签名与会话/请求序列生命周期绑定（重签 ILEGEL、verbatim 重放 OK；SF-013 三判据） | **G** 止损决议后 oracle/在线兜底 | 明示依赖、TTL、并发/恢复与未解字段；决议不能预设（止损决议门） |

### 案例与工时参考

| 策略 | 已实证案例 | 估计工时 |
|---|---|---|
| A | Bilibili GeeTest w = AES-128-CBC + RSA | 数小时-1天 |
| F | XHS x-mini-sig（50+ HMAC 爆破失败后的正解） | 2-4天 |
| C | XHS libtiny（546B 替代 7.95MB SO，8.5x 加速） | 半天-1天 |
| B | —（D-810 unflatten 后追踪重写） | 1-3天 |
| D | Apple Music SAP（CFF 200+ handler，send() 方案） | 1-2天 |
| E | Apple Music Unicorn 受阻后的备选 | 半天 |
| RSA | ct_client loginAuthCipher / e9hgat5k / 连信 CKey | 1-2天 |
| H | 盒马搜索 H1 / 猫眼 yanchu H1 / ele draft-29 | 档案已有则小时级 |
| G | 淘宝闪购 / me.ele MTOP（verbatim 重放 OK） | 半天-1天 |

---

## 混淆先分类：不直接套 CFF 系

> 命中「BCF/FLA/MBA、间接 BR/BLR、VM/时序反模拟」时，先分缺口再选路，别一上来就 D-810：

| 混淆形态 | 典型含义 | 选路 |
|---|---|---|
| BCF（基本块拆分） | 扁平化但结构可还原 | 先试 D-810（策略 B）；无效转局部传播 / trace |
| FLA / MBA（全域扁平化 + 混合布尔算术） | D-810 常失败，伪条件恒真 | 静态算子提取（F）或 trace+快照（C） |
| 间接 BR / BLR（跳转表间接化） | 调用链不可静态跟 | Stalker / tracked disasm；或会话提取（D） |
| VM / 时序反模拟 | 200+ handler；`RDTSC % N` 分支 | Unicorn 先查 RDTSC（SF-005）；VM 走 D，时序反模拟走 E |

---

## 假设结论 → 策略连线

> Phase 2 假设产出直接路由（多条件同时命中按核心表 first-match 从上到下裁决）：
> 假设1 标准算法 → 策略 A（重写）/ RSA（随机填充类）；假设2 标准变种 → 策略 A + KEY/IV/padding 枚举对拍（Phase 4.3）；
> 假设3 自定义/无常量 → 按形态路由：CFF（D-810 有效→B；D-810 无效+只读常量→C）、重度虚拟化 200+ handler→D、GF(2^8)→F、VMP→H；
> 生命周期绑定证据（SF-013 三判据）→ 直接跳 G，不再进假设循环；
> 反模拟检测（SF-005）阻断 Unicorn → 策略 E（Frida RPC 在线签名；重度虚拟化 SO 主选 D，Unicorn 受阻后备选 E）。

---

## D vs H 判定

静态形态重叠（都有 handler 分发）时看"轮换"——运行期多次采样同一输入，输出/上下文随时间变化（SF-017 慢速/间隔实验定性）→ H；不变 → D。可先按 D 会话提取，发现轮换证据即升级 H。反 hook checksum 等反检测维度（与枚举隐藏 SF-016 同级但独立）不改变策略选择，只决定注入对抗手段。

---

## 止损决议门（策略 G 专用）

🔴 在线兜底**不能预先写进计划**。只有已列尽假设、完成原版/传输/字段 diff、并由证据证明纯离线缺口依赖物理状态（SF-013 三判据：verbatim 重放=SUCCESS、重签=ILEGEL、t/过期已排除）后，才做止损决议。止损型交付明示 oracle、未解字段、生命周期，**不称纯算**。

---

## oracle 到手后要改请求？先跑 SF-018 隔离实验阶梯

（第1步 原样对照 → 第2步 重压缩改字节流 → 第3步 改语义）定位"哪个层可改"：query 可改（cursor/count + 重签）→ body 语义不可动。参数必需性按 SF-019 分两层验证（签名引擎出不出签名头 vs 服务端 status_code），增量砍参数实验，不要靠猜。
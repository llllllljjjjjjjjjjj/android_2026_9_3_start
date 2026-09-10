---
name: protocol-signature-reverser
description: 协议签名逆向专家。判因与三级交付（解析/绕过/止损）+ 开工门 + 参数谱系。专门还原APP的API签名算法（HTTP Header/URL参数/Body签名）。6路证据采集（SO triage/IDA静态/Capture抓包/Frida runtime/Emulator模拟/文献开源）+ 算法还原策略选择器（A-H/RSA）+ 生命周期绑定/混合加密/unidbg执行正确性止损 + 传输墙/止损型交付/设备令牌复用。
whenToUse: Android协议逆向、签名逆向、sign、x-mini、shield、mtgsig、MTOP、Gorgon、Argus、Perseus、unidbg、Unicorn、HMAC、RSA、设备令牌、会话绑定、在线oracle、fp_stack。
---

# Protocol Signature Reverser — 协议签名逆向专家

## 任务边界
本 Skill 是 Android 协议/签名的判因与三级交付负责人，不预设结果一定是纯算。


🗝️ **核心原则**: 从顶层往下分析 (Java/Retrofit → Native),不要从底层往上 (SSL → 自定义帧解析)。参考 SF-002。

> 🔴 **边界（与其他逆向 skill 分工）**：
> - APK/API/网络栈侦察 → `android-recon`
> - 脱壳取得真实 DEX/SO 段 → `android-unpack`
> - 运行期 Frida Hook / 反检测 / SSL 绕过 / SO 动态 trace → **android-dynamic**
> - 本 skill **只做**：把签名/加密算法**还原成离线可复现的纯算实现**（Python/C），并做字节级验证；含 unidbg 补环境（Phase 6）。

> ⏺️ **全程风控记录**：风控记录开关 YES 时（AGENTS.md），本 skill 执行全程遇到的风控素材随手记到 `projects/<target>/docs/risk-observations.md`——oracle 频率上限/批量签名/令牌软封/传输墙/生命周期绑定/重放可改层 + 任何不起眼但对风控对抗有用的点（格式见黑名单 15）。

> 🧰 **配套自建 MCP（无 UI，权威工作流见 [AGENTS.md]）** —— 
本 skill 横跨工作流**阶段 2↔3↔4 闭环**：
> - 阶段 2 静态定位：`reverse_index`（`list_suspicious_sign_methods`/`find_symbol`/`find_endpoint`/`search_strings`）在 `decompiled/` 找签名入口与调用链。
> - 阶段 3 算法假设：`algo_lab`（`analyze_signature_samples`/`detect_encoding`/`test_hash_candidates`/`test_hmac_candidates` 爆破/`generate_python_reproducer`+`verify_reproducer` 字节校验）。
> - 阶段 4 在线对拍：`frida_orchestrator` `frida_rpc_call` 把 SO/Java 函数当 oracle。
> - 抓包：`reqable`/`charles`（先链机场 7892，见 android-recon §3.5）；传输墙先 `projects/fp_stack/`。
> 🔧 **签名 SO 逆向工具（`tools\so-reverse\` 全套就位）**：重度/去混淆首选 IDA Pro；二线 Ghidra；radare2 体检；Flutter 用 blutter。unidbg 补环境照 Phase 6。

**主线流程**：
```
签名识别(Phase0) → 6路证据采集(Phase1) → 假设生成+区分实验(Phase2) → 策略选择(Phase3)
   → 纯算实现(Phase4) → 字节级验证(Phase5)；需脱离设备走 unidbg(Phase6)
```

## ⚠️ 开工门（每单攻坚前必须有 —— Phase 0.5 总闸门）

1. 一句目标能力（"还原 X 的 y 签名 → 可离线复现"）；
2. 最终判官（字节 oracle / 服务端语义 / 账号可见效果）；
3. 交付形态（解析型 / 绕过型 / 止损型）；
4. 可证伪成功标准（出现什么证据算胜、什么算败）；
5. 时间/成本/账号止损线；
6. 真实抓包 + 至少一组 input→output——**没有样本先采集，不进入 Phase 1**。

同时固定 App/APK/SO hash、ABI、设备 serial、账号/session、IP/代理、请求字节与时间；验证期**单设备单账号**，不批量发送无效签名，同接口同错误**连续 3 次**停止同类请求并归因。

## 🎯 先定位缺口层：按缺口选路，不做固定流水线

以下 Phase 0→6 是完整方法骨架，**不是每单必过的流水线**——先按成本选能闭合当前缺口的最短路径：

- 请求还未到业务网关 → 先查 DNS/TLS/ALPN/JA3/QUIC/私有隧道（与签名无关）；
- verbatim 原包可用、自建重签失败 → 算法输入 / 生命周期 / 序列态（SF-013）；
- 改 body/path 后字段不变 → 候选设备令牌，不先当每请求 HMAC（SF-019）；
- 原版 App 同环境也失败 → 先排环境/账号/IP/服务端（SF-004）；
- unidbg 能返回但与已知向量不一致 → 执行正确性问题，模拟执行不是 oracle（SF-014）。

> **终止性结论须持证据牌照**："被风控""服务器绑会话""随机生成""纯算完成"等裁决类话术，必须命中对应证据并留下路径，不口头判定：
> - "被风控" → SF-004：明文/空 body 对照证明错误码与加密无关；环境/账号/IP 已排除；记入 `projects/<target>/docs/risk-observations.md`（403/429/验证码/蜜罐/封禁码）；
> - "服务器绑会话" → SF-013 三判据：verbatim 重放=SUCCESS、旁路/重签=ILEGEL_SIGN、t/过期已排除；
> - "随机生成" → SF-012 修正版：非确定性 = 随机填充正常，验明文/key 来源/结构长度/解密验签，不追密文字节；
> - "纯算完成" → 解析型交付门：参数谱系零空洞 + ≥3 组非样例字节级一致 + 单变量实验落定（100+ 只作成熟确定性实现的增强回归）。
> 所有裁决在验证期**单设备单账号**下产出，附 oracle 类型与证据路径。

## 📦 三级交付（判因后的交付形态与话术；Phase 3 选策略前、Phase 5 交付前各过一遍）

| 形态 | 条件 | 可以怎么说 |
|---|---|---|
| 解析型 | 字段谱系零空洞，算法自包含，最低 3 组任意输入与 oracle 一致，动态字段单变量实验落定 | "已还原 / 离线纯算" |
| 绕过型 | 利用已验证的服务端/客户端条件，不等于算法还原 | 明示条件、脆弱性和版本 |
| 止损型 | 依赖真机、原 App、RPC、在线签名或时效 token | 明示 oracle、未解字段、生命周期 |

> `≥3` 是最低交付门；`100+` 只用于成熟确定性实现的增强回归，**不得反过来用数量掩盖字段谱系空洞**（覆盖并修正 SF-012 / Phase 5 旧"无条件 100+"表述）。RSA-PKCS1 随机填充等非确定性输出**不能要求密文字节相同**，应验证明文、key 来源、结构/长度和解密/验签结果。**在线兜底不能预先写进计划**——只有列完已穷尽假设、完成原版/传输/字段 diff、并由证据证明纯离线缺口依赖物理状态后，才做止损决议。

---

## 🔴 签名逆向高风险行动黑名单（每次开工/交付前必过）

> 每条对应一条完整失败案例（错误→正确→规则→成本），详述见 **[references/failure-modes.md](references/failure-modes.md)**（SF-001~SF-020，含触发→下一步速查表）。

1. **禁止** 在找到标准加密常量前就假设算法类型 (SF-001)
2. **禁止** HMAC/算法爆破超过 10 个组合 (SF-008)
3. **禁止** Unicorn 模拟前不检查 RDTSC/反模拟检测 (SF-005)
4. **禁止** 不验证字节级一致就说"还原了"（SF-012：解析型最低 3 组**非样例**输入与 oracle 字节级一致、成熟确定实现再追加 100+ 增强回归；RSA/随机填充类验明文/key 来源/结构长度/解密验签，**不追密文字节**）
5. **禁止** 跨 APP 复用签名算法假设 (XHS 是 GF 不代表别的也是)
6. **禁止** 忽略 opaque token 警告 (SF-006)
7. **禁止** 从底层往上分析超过 4 层 (SF-002)
8. **禁止** 跨设备复用签名密钥 (SF-009)
9. **禁止** 对生命周期绑定签名硬做纯离线 (SF-013：verbatim 重放 OK 而重签 ILEGEL → 转在线兜底)
10. **禁止** 把 unidbg"跑通"当解 (SF-014：先验执行正确性，CTR keystream 恒定=坏)
11. **禁止** 把批内快速采样的切换点当轮换周期结论 (SF-017：变间隔/慢速实验交叉验证)
12. **禁止** frida 枚举失败就当 App 死了 (SF-016：adb pidof → attach(pid) 直连)
13. **禁止** 修改 oracle 重放请求的 body 字段语义 (SF-018：cid 列表等会话状态绑定 → -99999；要改从 query 改)
14. **禁止** 未经砍参数实验就认定业务参数必需 (SF-019：7 参数全砍照过，签名引擎与服务端分两层验证)
15. 风控记录 YES（AGENTS.md 两开关）时，把签名/令牌软封/传输墙风控点记到 `projects/<target>/docs/risk-observations.md`：开关二 YES → 按 E-/F- 动态条目模板记完整条目；仅开关一 YES → 记一行；均 NO → 不记
16. **禁止** 批量试无效签名 / 单 IP 碰多号：验证期单设备单账号；同接口同错误**连续 3 次**停止同类请求、保存证据并归因


## 🧰 工具与版本时效性黑名单（2026-08-24 真机基线同步）

> 签名 oracle / 在线兜底策略（E/D/G）最依赖 Frida 环境，开工前先核对版本。真机基线权威源：AGENTS.md §2-§3。

| 项 | 状态 | 说明 |
|----|------|------|
| Frida 17.x | 🔴 **禁用** | 硬目标（XHS）所有模式秒退全挂；客户端版本必须与所选 server **严格对齐** |
| florida-server 16.5.9（魔改免杀） | ✅ 主力 | 真机 `/data/local/tmp/florida-server`，自报 16.5.10-dev.0；配 `.venv-frida-16.5.7` 客户端 |
| f1657（官方 16.5.7，重命名运行） | ✅ 回退 | 同上 venv；Florida 异常时切回 |
| frida-server 16.7.19（官方） | ⚪ 普通目标 | 配 `.venv-frida-16.7.19`；硬目标不用 |
| unidbg | JDK 17（🔴 禁 JDK 21，Module 类名冲突）| Maven 3.9.x 已验证 |
| 魔改 frida-server 进程名乱码 | 按名 attach 失败 → `enumerate_applications()` 按 identifier 取 pid | 淘宝 MTOP 案例 |
| frida Python RPC 方法名 | 必须全小写（Python 绑定 lower() 查找，camelCase 报 unable to find method）| dy oracle 坑② |
| 反枚举 App（dy 级） | frida 枚举失败 ≠ 进程死 → `adb shell pidof` 直连 attach(pid) | SF-016 |

---

## Phase 0：签名类型识别

先定位签名位置（Header / URL / Body）并按长度+编码评估复杂度（固定短→单次 HMAC/MD5；固定大→RSA/多层；变长 HEX→SHA-256；变长 Base64→二进制结构；>1000 chars→多步流水线）。完整位置表与复杂度树见 **[references/analysis-workflow.md](references/analysis-workflow.md)** Phase 0。

## Phase 1：6 路证据采集（可选并行，不机械全跑）

🔴 CHECKPOINT：采集前确认 SO 已获取、真机/模拟器已连、抓包已配、搜过 GitHub 同类逆向。六路是**可选证据源**，多路验证同一缺口时可并行，不机械全跑：
①SO triage（字符串/标准常量/壳/熵；搜不到≠不存在，可能 XOR/动态计算/flatten → SF-003；工具用 rabin2/strings/llvm-readelf）
②IDA/static（Java→JNI 边界、request builder、数据流、反汇编/伪代码/调用图；Ghidra GUI/headless 只作二线，GhidraMCP 当前仅 `documented`）
③Capture 抓包（含同请求两次/跨端点/跨时间验证清单；私有二进制先按连接时序重组，**高熵≠已加密**；原版请求的 raw method/path/query/header/body、时序、前置接口和响应；二进制先保留原字节，再做 Protobuf wire 侦察）
④Frida/runtime（按安全等级选深度；枚举失败先 `adb shell pidof` → SF-016；最窄边界的入参/出参/调用栈/RPC oracle；由 `android-dynamic` 选择注入方式）
⑤Emulator 模拟（Unicorn：先查 RDTSC → SF-005；unidbg 见 Phase 6，先验执行正确性 → SF-014；unidbg/Unicorn/frozen blob/算子提升；先用已知向量证明执行正确，再当 oracle）
⑥References 开源实现、论文、版本差异；记录来源/许可证，只把当前样本能验证的规则纳入结论。
各路命令/代码/参考表见 analysis-workflow.md Phase 1。

私有二进制 Capture 先按方向、连接和时序重组字节流，再用多样本验证 magic/length/端序/TLV/sequence/checksum 与状态机。TCP segment、PSH 或一次 `recv()` 都不是消息边界；高熵也不是“已加密”的证据，须继续排除压缩、编码、分块和混合结构。

跨版本迁移先固定新旧 SO hash/ABI，以 export、字符串引用、常量和调用关系建立候选锚点。BinDiff/LLM 映射只能生成候选；关键函数必须用反汇编结构或同输入运行向量复核后才能沿用。


## Phase 2：假设生成与验证

🔴 先跑 SF-008（假设/爆破超 10 个组合就停，转反汇编+算子提取）。生成竞争假设（标准算法 / 标准变种 / 自定义，**再加设备态/会话态/传输指纹类**），**每轮最多保留 2-3 个能被下一实验区分的假设**；**假设不是交付物，每轮必产出证据锚点或下一个区分实验**。做三重验证：输入输出字节一致、跨请求一致性、跨设备一致性（Y_A≠Y_B=含设备密钥）。假设模板、区分实验与验证协议见 analysis-workflow.md Phase 2。

## Phase 3：算法还原策略选择器

> 🔴 选择策略后 🛑 STOP，展示选择理由给用户确认再执行。完整策略表（含案例/工时）、假设→策略连线、混淆先分类、D vs H 轮换判定、oracle 改造阶梯、止损决议门见 **[references/strategy-selector.md](references/strategy-selector.md)**。

| 证据 | 策略 | 验收 |
|---|---|---|
| 标准常量、输入链清楚（AES S-box / SHA K表 / HMAC 魔数；SF-001） | **A** 标准库重写 | canonical bytes、key/IV/padding，最低 3 组非样例 oracle 一致（成熟后 100+ 回归） |
| GF(2^8) 字节变换、无标准常量 | **F** IDA 反汇编→算子序列→frozen op list | 非样例输入逐字节一致 |
| 固定执行路径依赖大 SO 只读状态（CFF 重度 + D-810 无效） | **C** Frozen Blob / 快照 | blob 来源、重定位、版本边界、oracle 对拍 |
| CFF 混淆 + D-810 有效 | **B** D-810 unflatten → 追踪 → 重写 | 反汇编结构复核后重写，oracle 对拍 |
| 定制虚拟化 200+ handler / 跳转表 | **D** Frida 会话提取→离线签名 | 会话重放 / 离线签名稳定复现 |
| 反模拟检测（RDTSC 等）+ SO 不复杂 | **E** Frida RPC 在线签名 | 真机 oracle 对拍；明示设备/session 依赖（止损型） |
| BCF / FLA / MBA、间接 BR/BLR、或 VM/时序反模拟 | **先分类缺口**：局部传播 / trace+快照 / Unicorn / unidbg，不直接套 CFF 系 | 反汇编边界 + 已知向量对拍，再任意输入 |
| RSA-PKCS1 随机填充 / 混合加密（密文每次不同） | **RSA** hook 加密原语入参→重建结构 | 可解密/验签、字段谱系与长度；**不追密文字节**（SF-012） |
| 裸 HTTPS/QUIC 协商失败、原版同环境能通（请求未到网关） | **H** 传输复刻 `projects/fp_stack/` | verbatim 请求先通，再判断签名（SF-020） |
| 生命周期绑定（verbatim 重放 OK、重签 ILEGEL；SF-013 三判据） | **G** 止损决议后 oracle/在线兜底 | 明示依赖、TTL、并发/恢复与未解字段；**决议不能预设** |

> 多条件命中按 first-match 从上到下；生命周期证据直接跳 G；反模拟阻断 Unicorn 走 E；混淆不能直接归类到 B/C/D/E 时，先按 BCF/FLA/MBA/间接 BR·BLR/VM 分类缺口再选。

## Phase 4：纯算实现

按选定策略实现：C=Frozen Blob（monkey-patch memory.read 记录字节读取→blob→AOT 预编译）；F=GF(2^8) Op List（序列化 madd/eor/ubfx 等算子→Python lift）；A=标准库（hashlib/hmac/Crypto.Cipher，对齐 KEY/IV/padding/mode）。步骤骨架与代码见 **[references/analysis-workflow.md](references/analysis-workflow.md)** Phase 4。Phase 4.5 AI 辅助（reverse-index/algo-lab/ida-pro/frida-orchestrator MCP 流 + JavDB/头条/eShard 案例 + Hook 生成提示词）同见该文件 Phase 4.5。

## Phase 5：验证与文档（强制）

🛑 **按三级交付门验收（SF-012 修正版）**：解析型最低 **3 组非样例输入**与 oracle 字节级一致（确定性实现；成熟后再追加 100+ 随机增强回归）；RSA/随机填充类验明文、key 来源、结构/长度与解密/验签结果，**不追密文字节**。**端到端 status_code/code==0 只算中间证据**——最终判官 = 服务端语义 / 账号可见效果 / 解密·验签成功 / 与真实 oracle 字节级一致。产出必须含**参数谱系表**（逐字段：来源 / 生成算法 / 生命周期/绑定 / 单变量验证，模板见 analysis-workflow.md Phase 5）。字节级/端到端验证代码与产出文档模板同见该文件 Phase 5。

---

## 案例速查（索引）

> 每个案例的算法/策略/坑/产物路径完整内容见 **[references/case-library.md](references/case-library.md)**。

| 案例 | 算法形态 | 策略 |
|------|---------|------|
| XHS x-mini-sig | GF(2^8) flattened + SHA-256 tail | F |
| XHS Shield | 白盒 AES→变种 MD5→RC4→Base64（跨版本稳定） | A |
| Apple Music ActionSignature | FairPlay SAP（ECDH+HMAC+AES-CTR，200+ handler） | D |
| Bilibili GeeTest w | Base64+AES-128-CBC+RSA PKCS1v15 | A |
| ct_client（爱加密/电信） | 凯撒 / AES g.t / RSA-PKCS1 loginAuthCipher / RSA+AES e9hgat5k | RSA+A |
| 连信（梆梆） | Content-CKey RSA/PKCS1 + body AES-ECB-PKCS5 | C+静态 |
| 淘宝闪购/me.ele MTOP | x-sign 生命周期绑定，纯离线不可行 | **G 止损** |
| 抖音 38.0.0 八神 | Gorgon/Argus/Ladon/Khronos，VMP+~0.5s 轮换密钥；oracle 重放 query 可改/body 语义不动 | **H 在线 oracle** |
| 瑞幸 q/sign + 同盾 blackBox | AES-ECB+分段 MD5；blackBox 真值 26 字符（非数美 3000B） | A |
| Keeta/猫眼 mtgsig | 请求无关设备令牌（a5/a7/a8/a9 不变）；s-ca-signature HMAC 纯算 | A+H1 |
| 盒马搜索 | 止损型：活机四头+fp_stack H1 verbatim，**禁止称四头纯算** | H 止损 |
| Play login v2 / MinuteMaid | #1/#123/#266 字节级，卡 #2 sealed env | 部分解析+止损 |

---

## Phase 6：unidbg 补环境（SO 离线模拟）

> 完整补环境表、标准步骤、经验表、jar 化三种交付形态、权威链接见 **[references/unidbg.md](references/unidbg.md)**。

- **环境**：JDK 17 + Maven（🔴 禁 JDK 21，Module 类名冲突）；关键步骤是必须 `callJNI_OnLoad`（多数 so 在其中 RegisterNatives）。
- **三边界先判**：完全离线常死结（FairPlay 类需服务器密钥交换）；一次性联网建 session 可行但工程量大；Frida RPC 设备在线最快。**补环境能脱离 App/设备，但未必脱离网络。**
- 🔴 **生命周期绑定/会话态（SF-013）unidbg 同 SO 也被拒 → 不投入，转 G/H 在线。**
- **jar 化交付门槛**：SO 已能补环境跑通就不重写算法，直接 jar 化；但必须先 Java `main()` 与真机字节级对拍（SF-012）+ 验执行正确性（SF-014 CTR keystream 恒定=执行坏），通过才打 jar，fat jar 必须 shade 打全依赖。

---
---

## 🚫 不要做（总纲速记）

> 黑名单按失败案例编号；这里是 9_month 合并后的原则级清单，开工/交付前各扫一遍：

1. 不从 TLS 帧等最底层开始，除非上层边界已证明不可达（SF-002）
2. 不把抓包长 blob、设备 token 或服务端透传字段**默认当本地签名算法**——先做参数谱系定来源（静态/本地生成/服务端下发/派生），上游下发值不当算法硬撕（SF-019，见 Phase 5 参数谱系）
3. 不跨设备复用密钥/令牌、不批量试无效签名、不在单 IP 碰多号（SF-009 / 黑名单 16）
4. 不把 unidbg 返回值、Frida RPC、verbatim 重放或 HTTP 200 包装成纯算（三级交付止损型 + Phase 5 判官）
5. 不为追求"字节一致"错误处理带随机填充的合法密码方案（SF-012 修正版：验明文/结构/解密，不追密文字节）
6. 不在谱系有空洞、动态字段未做单变量实验、没有真实判官时报告完成（三级交付解析型门 + 证据牌照）

---

## 自进化机制

- 每次成功逆向新签名 → 追加到案例速查（references/case-library.md）
- 每次发现新失败原因 → 追加到失败模式（references/failure-modes.md）
- 每次验证新策略有效 → 更新策略选择器（references/strategy-selector.md）

进化触发词：`记录签名逆向` / `更新算法案例`

---

# 参考资料（references/，按需加载）

| 文件 | 内容 | 何时读 |
|------|------|--------|
| [references/failure-modes.md](references/failure-modes.md) | SF-001~SF-020 完整失败案例/规则/成本 + 触发→含义→下一步速查表 | 开工前过一遍、踩坑时对照 |
| [references/strategy-selector.md](references/strategy-selector.md) | Phase 3 策略「证据→策略→验收」表（A-H/RSA/G）、案例/工时、混淆先分类、假设连线、D vs H、oracle 改造阶梯、止损决议门 | 选定还原策略时 |
| [references/analysis-workflow.md](references/analysis-workflow.md) | Phase 0/1/2/4/4.5/5：识别、6 路证据采集、区分实验、纯算实现、AI 辅助、字节验证、三级交付验收与参数谱系模板 | 采集/假设/实现/验证各阶段 |
| [references/case-library.md](references/case-library.md) | 全部 APP 案例算法/策略/坑/产物路径 | 复用同类 APP 经验 |
| [references/unidbg.md](references/unidbg.md) | Phase 6 补环境表、标准步骤、jar 化交付 | SO 离线模拟、jar 化 |

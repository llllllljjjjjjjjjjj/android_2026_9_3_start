# 签名分析工作流（Phase 0/1/2/4/4.5/5 详细方法）

> 本文件由 `SKILL.md Phase 0/1/2/4/4.5/5` 引用，属于**按需加载**层：签名类型识别、6 路证据采集、假设与区分实验、纯算实现（Frozen Blob / GF Op List / 标准重写）、AI 辅助协议分析、字节级验证、三级交付验收与参数谱系模板时读。策略选择框图见 strategy-selector.md，unidbg 见 unidbg.md。

---

## Phase 0：签名类型识别

### 0.1 签名位置

| 位置 | 格式 | 案例 |
|------|------|------|
| HTTP Header | `x-mini-sig: <hex>` | XHS |
| HTTP Header | `X-Apple-ActionSignature: <base64>` | Apple Music |
| HTTP Header | `x-sign` / `x-umt` / `x-sgext` / `x-mini-wua` | Ele.me / 盒马 MTOP |
| HTTP Header | `mtgsig` / `s-ca-signature` | 猫眼 / Keeta |
| HTTP Header | `X-Gorgon` / `X-Argus` / `X-Ladon` / `X-Perseus` | 抖音 |
| URL/Body | `q=` / `sign=` / `blackBox` | 瑞幸 |
| URL 参数 | `?w=<enc>&shield=<enc>` | Bilibili / XHS |
| Body 字段 | `{shield: "<hex>"}` | XHS |
| Body 字段 | protobuf 嵌入 | XHS metrics_report |

### 0.2 签名复杂度评估

```
签名长度
    ├─ 固定长度 + 小 (< 64 chars) → 可能是单次 HMAC/MD5
    ├─ 固定长度 + 大 (64-256 chars) → 可能是 RSA 签名 / 多层序列化
    ├─ 变长 + HEX → 可能是 SHA-256 类
    ├─ 变长 + Base64 → 可能是二进制结构 (Apple Music 501B → 668 chars)
    └─ 极长 (> 1000 chars) → 可能是多步流水线 (XHS MUA ~1124 chars)
```

> ⚠️ 复杂度只作初判线索，不作结论：`改 body/path 后字段不变` → 候选设备令牌，不先当每请求 HMAC（SF-019）；先做字段谱系（Phase 5 模板）再谈算法。

---

## Phase 1：6 路证据采集（可选并行，不机械全跑）

> 🔴 **CHECKPOINT**: 启动采集前，先确认: SO 文件已获取? 真机/模拟器已连接? Reqable/mitmproxy/ecapture 已配置? 搜过 GitHub 同类逆向了吗?

> 六路是**可选证据源**，多路能验证同一缺口时可并行，不要求机械全跑（按缺口选路，见 SKILL.md「先定位缺口层」）。统一编号 / 命名与 SKILL.md 一致。

```
                  用户输入"逆向 X APP 的签名"
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                  ▼
   [有SO文件]         [有真机设备]        [开源参考]
        │                 │                  │
   ┌────┴────┐      ┌────┴────┐        ┌────┴────┐
 ①SOtriage ②IDA静态 ③Capture ④Frida/runtime ⑤Emulator ⑥References
  字符串/壳熵 Java→JNI  抓包    最窄边界Hook   Unicorn/unidbg  文献+开源
```

### 路1: SO triage（字符串 + 常量 + 壳/熵）

工具：`tools\so-reverse\` 的 rabin2/strings/llvm-readelf（imports/exports/壳与熵初判）+ IDA 搜索。

```python
# 搜索加密常量
# AES S-box 首字节 0x63
find_bytes: "63 7C 77 7B F2 6B 6F C5"
# SHA-256 K 表首字 0x428a2f98
find_bytes: "42 8A 2F 98 71 37 44 91"
# MD5 T 表
find_bytes: "D7 6A A4 78 E8 C7 B7 56"
# ChaCha20 "expand 32-byte k"
find_strings: "expand 32-byte k"
# CRC32 表
find_bytes: "00 00 00 00 77 07 30 96"
```

**搜索不到常量 ≠ 不是这些算法**（SF-003）。常量可能：
- 被 XOR 混淆存储
- 运行时动态计算（从多项式中即时生成）
- 被展开为算术序列（GF 矩阵 → flattened op list）

### 路2: IDA/static 深度分析（Java→JNI 边界/数据流/反汇编）

- jadx/apktool 反编译 → 找 request builder 与签名入口、Java→JNI 边界（SF-002 顶层切入）；
- IDA 反汇编/伪代码/调用图；重度反编译首选 IDA，Ghidra GUI/headless 仅作二线；
- 跨版本迁移：**先固定新旧 SO hash/ABI**，以 export、字符串引用、常量和调用关系建立候选锚点；BinDiff/LLM 映射只生成候选，关键函数必须用反汇编结构或同输入运行向量复核后才沿用；
- 壳/加固先行（SF-007 wrapper、SF-011 malformation），D-810 无 UI 激活自查见 android-dynamic §5.1。

### 路3: Capture 动态抓包（raw 请求/前置接口/时序）

```powershell
# XHS / 强 pinning APP
mitmdump --mode transparent --listen-port 8080
adb shell "su -c 'iptables -t nat -A OUTPUT -p tcp --dport 443 -j REDIRECT --to-port 8080'"

# 普通 APP
# 用 Reqable + TrustMeAlready

# 阿里系 (ANet/MTOP, taobao/eleme): 核心走 ANet→libtnet(内部BoringSSL)+libxquic(QUIC), 旁路系统代理/系统libssl
#   → Reqable 抓 6 万条 0 mtop。Hook libxquic xqc_h3_request_send_headers/send_body 拿加密前明文
#   → 纯 native 不触发 quicksparrow；libxquic 后加载需 re-arm（见 android-recon §3.4）
```

**抓包验证清单**：
- [ ] 同一请求两次 → 签名相同？（有状态/无状态）
- [ ] 不同 API 端点 → 签名算法相同？（算法 vs 端点特定）
- [ ] 不同时间 → 时间戳是否参与签名？
- [ ] 保留**前置接口和响应**、完整原请求的 raw method/path/query/header/body 与时序

**私有二进制 Capture 纪律（协议 + framing，勿当加密定论）**：
先按方向、连接和时序重组字节流，再用多样本验证 magic/length/端序/TLV/sequence/checksum 与状态机；**TCP segment、PSH、单次 `recv()` 都不是消息边界**，高熵也不是"已加密"的证据——须继续排除压缩、编码、分块和混合结构。

### 路4: Frida/runtime（最窄边界 + RPC oracle）

按 APP 安全等级选择 Hook 深度：

```javascript
// L0 (Bilibili级): 直接 Hook Java 签名函数
var SignUtil = Java.use("com.bilibili.lib.SignUtil");
SignUtil.sign.implementation = function(params) {
    console.log("[+] sign input:", params);
    var result = this.sign(params);
    console.log("[+] sign output:", result);
    return result;
};

// L1-L2 (Apple Music/Ele.me级): Native Hook
var sign_func = Module.findBaseAddress("libstoreservicescore.so").add(0x1979E0);
Interceptor.attach(sign_func, {
    onEnter: function(args) {
        console.log("[sign] input:", hexdump(args[2], {length: args[3].toInt32()}));
    },
    onLeave: function(retval) {
        console.log("[sign] output:", hexdump(retval));
    }
});

// L3 (XHS级): 调 APP 内置接口，不 Hook 签名层
// 见 frida_report.js — Java.use NoteActionService
```

- 记录最窄边界的入参/出参/调用栈；Frida RPC 把函数当 oracle（frida_rpc_call，方法名全小写，见工具黑名单）。
- **枚举失败 ≠ 进程死**（SF-016）：frida 枚举不见目标 → `adb shell pidof <pkg>` 拿真实 pid → `dev.attach(pid)` 直连。

### 路5: Emulator 模拟（Unicorn/unidbg，条件性使用）

**⚠️ 先检查反模拟检测（SF-005）**：
```python
# 在 IDA 中搜索：
# RDTSC / RDTSCP / CNTVCT_EL0 / PMCCNTR_EL0
# mrs x0, cntvct_el0
# gettimeofday / clock_gettime
# /proc/self/maps (检测模拟环境)
```

**如果有 RDTSC**（Apple Music 经验）：
- 方案 A：暴力搜索 mod-N 值（3 种分支）
- 方案 B：Frida Stalker trace 记录每一步 dispatch
- 方案 C：放弃 Unicorn → Frida RPC（策略 E）

**如果无反模拟检测**：
```python
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM
# 加载 SO segments → 初始化堆栈 → Hook 关键调用 → 执行
```

unidbg 补环境见 Phase 6 / unidbg.md；**把模拟器当 oracle 前先验执行正确性**（SF-014：重复 keystream/全零状态=执行坏，见 unidbg.md「执行正确性红灯清单」）。

### 路6: References（文献 + 开源实现对照）

```
搜索策略：
- "<APP名> signature algorithm reverse"
- "<SO文件名> analysis"  
- "github <APP名> shield/sign algorithm"
- "<APP名> API protocol reverse engineering"
```

| APP | 算法 | GitHub 参考 |
|-----|------|-------------|
| XHS Shield | white-box AES+MD5+RC4 | RedNote/Xiaohongshu-Shield-Algorithm |
| GeeTest | AES+RSA | 多个 Python 实现 |
| FairPlay | ECDH+HMAC-SHA256 | 学术论文（协议级） |
| 通用 MTOP | HMAC-MD5 | 阿里 MTOP SDK 开源版 |

> 记录来源/许可证；**只把当前样本能验证的规则纳入结论**，不跨 APP 复用算法假设。

---

## Phase 2：假设生成与区分实验

> 🔴 **CHECKPOINT**: 在生成假设前先跑 SF-008 检查 — 已尝试了多少个算法假设? 超过 10 个 → 🛑 **STOP**，不要继续生成假设，切换到反汇编+算子提取路径。

### 2.1 假设模板（每轮最多保留 2-3 个能被下一实验区分的假设）

```
算法类：
假设1: 标准加密算法（HMAC-SHA256 / AES-CBC / RSA签名）
  → 证据：找到标准常量、标准输出长度
假设2: 标准算法变种（改变 padding/IV/迭代次数）
  → 证据：输出长度标准但内容不匹配
假设3: 自定义算法（GF变换 / 私有密码学）
  → 证据：无标准常量、输出无规律、SO 内有大型状态机

非算法类（谱系候选，先于算法硬撕）：
假设4: 设备令牌/服务端透传（改 body/path 字段不变 → 见路"缺口定位"，SF-019）
假设5: 会话/请求序列绑定（verbatim 重放 OK、重签 ILEGEL → SF-013）
假设6: 传输指纹或私有协议（请求未到网关 → fp_stack，SF-020）
```

**假设不是交付物**——每轮必产出证据锚点或下一个区分实验，否则不进入下一轮。

### 2.2 三重验证协议

**验证 1: 输入输出一致性**
```
Python(已知输入) → 算法候选 → output_A
SO(已知输入)      → native call → output_B
assert output_A == output_B  # 字节级（确定性算法；RSA 类见 SF-012 非字节级规则）
```

**验证 2: 跨请求一致性**
```
Request 1: path=/api/a, body=x → 签名 P1
Request 2: path=/api/b, body=y → 签名 P2
→ 验证 P1/P2 中哪些部分变化、哪些固定 → 推断签名结构
```

**验证 3: 跨设备一致性**
```
设备 A: input=X → output=Y_A
设备 B: input=X → output=Y_B
→ Y_A != Y_B = 算法含设备密钥
→ Y_A == Y_B = 算法无状态/无设备绑定
```

### 2.3 区分实验（优先顺序）

1. 同一有效原始字节在允许的失败预算内重放，观察稳定/漂移；
2. 原版 App 同设备/账号/IP 对照；
3. 全量流量 diff（含前置接口与埋点）；
4. 单变量改变 method/path/query/body/header/time/device/session；
5. 必要时轮换一个维度，**禁止单 IP 同时碰多号**。

连续尝试 10 个 HMAC/hash 拼接候选仍无证据提升 → 停止爆破，转静态/动态算子提取（SF-008）。

---

## Phase 4：纯算实现

### 4.1 Frozen Blob 方法（策略 C）

```
步骤:
1. Monkey-patch SO 加载器的 memory.read()
   记录 [0xSO_BASE, 0xSO_BASE+SO_SIZE) 范围的字节读取
2. 调用签名路径（任意确定性输入，路径固定）
3. 收集 (addr, byte_value) → 合并连续区段 → binary blob
4. 写 Python 模块：
   - 复用 AArch64/x86_64 指令解释器
   - load_frozen_into_memory() 替代 load_elf_segments()
5. AOT 优化：路径预编译为 closure 列表 + 寄存器索引化
6. 验证：≥3 组非样例 SO vs Blob 字节级一致起步，成熟确定性实现追加 100+（SF-012）
```

### 4.2 GF(2^8) Op List 方法（策略 F）

```
步骤:
1. IDA 反汇编签名函数 → 识别所有 GF(2^8) 算子
   (madd/umull/eor/and/orr/ubfx/bfi/lsl/lsr/extr 组合)
2. 按执行顺序序列化算子 → JSON ops list
3. Python lift: 每条算子 → 对应的 Python int/numpy 操作
4. 验证：已知输入 → Python output == 真机 output（字节级，≥3 组起步）
```

### 4.3 标准算法重写（策略 A）

```python
# 确认以下参数后直接使用标准库：
import hashlib, hmac
from Crypto.Cipher import AES

# 验证 KEY/IV/padding/mode 与真机一致
# 验证：≥3 组非样例字节级起步；成熟确定性实现追加 100 组随机输入
```

---

## Phase 4.5: AI 辅助协议分析 (🆕 2026 v2)

### MCP 工具链自动化流

```
LLM
  │
  ├─ reverse-index-mcp: index_project → list_suspicious_sign_methods / find_symbol / search_strings
  ├─ algo-lab-mcp: analyze_signature_samples → test_hash/hmac_candidates → generate_python_reproducer + verify_reproducer
  ├─ reqable / charles: 抓样本（先链 7892；A14 CA 见 android-recon §1.3）
  ├─ ida-pro-mcp: analyze_function / xrefs / D-810 无 UI 激活（android-dynamic §5.1）
  ├─ frida-orchestrator-mcp: frida_rpc_call 当 oracle
  └─ fp_stack: 传输墙先过再谈签名（SF-020）
```

### AI 驱动案例速查

#### Case A: JavDB — 全自主逆向 (7 messages, <5 min human time)
- AI 自主: 反编译 APK → 提取 124 个 API → 逆向 ARM64 `jdsignature` → 派生 native key generation (APK signing cert DER bytes)
- 产出: 5,422 行 OpenAPI spec + Python SDK
- 关键: AI 读了 ~3000 行 ARM64 汇编,无人类逆向经验介入

#### Case B: 头条 APP — 15+ iterations 才找到正路
- ❌ 尝试: SSL hooking → Cronet native → HTTP/2 frame parser (700行 JS in Frida, RFC 7541 HPACK+Huffman!)
- ✅ 最终: 88 行 Java Retrofit interceptor Hook → 一条语句截获所有请求
- **教训 SF-002**: 从顶层往下,不要从底层往上

#### Case C: eShard TTD — 7B 指令 AI 自主分析
- AI 分析 Telegram Android 70 亿条 ARM64 指令 trace
- 10 分钟内无人工引导: 重建 MTProto v2 解密链,识别 6 种活动 (AES-IGE/SQLite/libyuv/JNI)
- 原材料: 纯 CPU 指令 + 寄存器值 + 内存读取

### AI 辅助 Hook 生成

```
提示词模板:
"在 JADX 中找到包 com.xxx.sign 下所有方法,
 分析签名算法的输入输出,
 生成 Frida Hook 脚本,
 捕获 3 组对应输入输出用于算法验证"
```

---

## Phase 5：验证与文档（强制）

> 🛑 **STOP**: 这是最终验证关卡。**按三级交付门验收（SKILL.md）**，SF-012（修正版）：解析型最低 **3 组非样例**输入与 oracle 字节级一致（成熟确定性实现追加 100+ 增强回归）；RSA/随机填充等非确定性输出验明文/key 来源/结构长度/解密验签，不追密文字节。未验证不说完成。

### 5.1 字节级验证（确定性算法强制）

```python
# 3 组非样例输入起步，成熟后 100+ 增强回归
samples = [os.urandom(32) for _ in range(3 if early else 100)]
for random_input in samples:
    py_output = pure_python_sign(random_input)
    so_output = call_so_sign(random_input)  # 或抓包对比
    assert py_output == so_output, f"Mismatch at iteration {i}"
    # → 全部通过 = 算法完全还原
```

### 5.2 端到端验证（中间证据，定最后判官）

```python
# 完整请求验证
headers = build_headers(url, method, body, params)
response = requests.get(url, headers=headers)
assert response.status_code == 200
assert response.json()["code"] == 0
```

> ⚠️ **HTTP 200、`code=0`、长度正确、JSON/Protobuf 可解析、framing 正确都只算中间证据**——最终判官必须是服务端语义、账号可见效果、解密/验签成功，或与真实 oracle 的字节级一致。

> 📝 **记录前**：风控记录 YES 时，把签名逆向得到的**请求约束**记到 `projects/<target>/docs/risk-observations.md`：oracle 调用频率上限/批量签名、令牌或设备密钥软封、传输墙（JA3/QUIC 被拒）、签名生命周期绑定（重放 vs 重签）、oracle 重放可改层（query 可改 body 不可改）；**以及清单外任何你认为对抗风控可能用得上的点（哪怕不起眼）**（格式见 SKILL.md 黑名单 15）。

### 5.3 参数谱系表 + 产出文档模板

> **参数谱系**（低谷判定与交付的核心）：每个 header/query/body/嵌套字段一行，来源只允许：静态常量、本地生成、服务端下发、由已知字段派生。

| 字段 | 来源 | 生成算法 | 生命周期/绑定 | 单变量验证 |
|---|---|---|---|---|
| `token` | 服务端下发/接口 | 透传 | session/TTL | 过期与刷新对照 |
| `x-sign` | 本地生成 | 精确输入与算法 | 单次/序列态 | 改一个输入后 oracle 对拍 |
| `deviceId` | 设备态 | 首启生成/存储路径 | 设备长期 | 换设备/清数据对照 |

> 抓包值若直接复用，标为 **"重放值+时效"**；调用真机/原 App 取值，标为 **oracle**。字段分类先做纯算、设备态、透传/会话态，避免把上游下发值当算法硬撕。

```markdown
## [APP名] [签名名] 逆向完成

- 交付形态: [解析型 / 绕过型 / 止损型]  （止损型须列出依赖与未解字段）
- 算法: [准确描述]
- 输入: [格式 + 示例]
- 输出: [格式 + 长度]
- 密钥: [来源 / 固定值 / 设备绑定]
- 有状态: [是/否]
- 跨版本稳定性: [已验证/未验证]
- 纯算实现: [文件路径]
- 性能: [N requests/s]
- 验证: [[N] 组非样例字节一致 / 解密·验签成功 / 服务端语义（判官类型）]
- 参数谱系: [见上方表格]
```
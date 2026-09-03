---
name: protocol-signature-reverser
description: 协议签名逆向专家。专门逆向APP的API签名算法（HTTP Header签名、URL参数签名、Body签名）。6路并行分析框架（SO静态/动态抓包/Frida Hook/Unicorn模拟/文献/开源参考）+ 算法还原策略选择器 + 生命周期绑定/混合加密/unidbg执行正确性止损 + 传输墙/止损型交付/设备令牌复用。触发词：签名逆向、sign破解、x-mini、x-sign、shield、mtgsig、q/sign、八神、gorgon、perseus、协议破解、算法还原、signature reverse、加密参数逆向、ct_client、e9hgat5k、loginAuthCipher、凯撒、滑块、CKey、MTOP、生命周期绑定、在线兜底、unidbg、混合加密、RSA随机填充、fp_stack、止损型。
whenToUse: 用户提到签名逆向、sign 破解、x-mini、shield、unidbg、算法还原、MTOP、加密参数逆向、生命周期绑定时
---

# Protocol Signature Reverser — 协议签名逆向专家

## 角色定位

你是 API 签名逆向专家。本技能 v2 融合：
- XHS/Apple Music/Ele.me/Bilibili/ct_client(爱加密电信)/连信(梆梆)/淘宝闪购(MTOP) 实战经验
- **2026 AI 驱动协议分析案例** (JavDB full auto / 头条 15+ iterations / eShard TTD)
- **MCP 工具链集成** (JADX-AI-MCP / apktool-mcp / Android Proxy MCP)
- 女娲式 6 路并行 + 达尔文式质量验证

🗝️ **核心原则**: 从顶层往下分析 (Java/Retrofit → Native),不要从底层往上 (SSL → 自定义帧解析)。参考 F-017。

> 🔴 **边界（与其他逆向 skill 分工）**：
> - 反编译/提取 API/抓包通路 → **android-recon**
> - 脱壳取真实 DEX → **android-unpack**
> - 运行期 Frida Hook / 反检测 / SSL 绕过 / SO 动态 trace → **android-dynamic**
> - 本 skill **只做**：把签名/加密算法**还原成离线可复现的纯算实现**（Python/C），并做字节级验证；含 unidbg 补环境（§Phase 6）。

> 🧰 **配套自建 MCP（无 UI，权威工作流见 [AGENTS.md](../../../AGENTS.md)）** —— 本 skill 横跨工作流**阶段 2↔3↔4 闭环**：
> - 阶段 2 静态定位：`reverse_index` —— `list_suspicious_sign_methods` / `find_symbol` / `find_endpoint` / `search_strings` 在 `decompiled/` 找签名入口与调用链。
> - 阶段 3 算法假设：`algo_lab` —— `analyze_signature_samples`、`detect_encoding`、`test_hash_candidates`/`test_hmac_candidates` 爆破、`generate_python_reproducer`+`verify_reproducer` 字节级校验。
> - 阶段 4 在线对拍：`frida_orchestrator` `frida_rpc_call` 把 SO/Java 函数当 oracle。
> - 抓包：官方 `reqable` / `charles`（先链机场 7892，见 android-recon §3.5）；传输墙先 `projects/fp_stack/`。
（上面的 JADX-AI-MCP / apktool-mcp 为可选外部 MCP；自建三件套是主路径。）
> 🔧 **签名 SO 逆向工具（本机 `tools\so-reverse\` 全套已就位）**：重度/去混淆**首选 IDA Pro**；二线 Ghidra `ghidraRun.bat` 对照；radare2 `rabin2` 体检；Flutter 签名用 `blutter\blutter.py`。unidbg 补环境仍照 §Phase 6。

**基于以下实战项目提炼**：
- XHS x-mini-{sig,mua,s1}：GF(2^8) flattened transform（50+ HMAC 爆破失败后的正确解）
- XHS Shield：白盒 AES → 变种 MD5 → RC4 → Base64（跨版本稳定）
- Apple Music X-Apple-ActionSignature：FairPlay SAP + CFF 分布式虚拟化（200+ handlers）
- Bilibili GeeTest w：AES-128-CBC + RSA PKCS1v15（标准算法，字节一致）
- ct_client（爱加密/电信）：loginAuthCipher=pad$+RSA-PKCS1；e9hgat5k=msec 混合加密 token；短信=明文JSON+凯撒；滑块=CV+g.t(AES-ECB)
- 连信（梆梆）：Content-CKey=RSA/PKCS1(16随机字母)，body=AES-ECB-PKCS5（梆梆内存dump脱壳后还原）
- 淘宝闪购/me.ele MTOP：x-sign 生命周期绑定 → 纯离线不可行 → 在线兜底（SF-013）
- Ele.me x-sign：MTOP 协议签名（待逆向）
- 瑞幸 q/sign：liblka-secure AES-ECB + 分段 MD5，纯算 e2e 200；同盾 blackBox=26 字符（不是 3000B 数美 blob）
- 抖音八神：Gorgon/Ladon/Argus/Khronos 字节级；X-Perseus P=679（CF3F 弹性杠杆）
- Keeta/猫眼 mtgsig：设备令牌（a5/a7/a8/a9 跨请求不变）；猫眼 a2+key36 已纯算；传输走 fp_stack H1
- 盒马搜索：止损型（活机四头 + fp_stack H1）；**禁止称四头纯算**
- Play login v2 / MinuteMaid DG：#1/#123/#266 字节级，卡 #2 sealed env

```
签名识别 → 6路并行采集 → 假设生成 → 三重验证 → 策略选择 → 纯算实现 → 字节验证
```

---

# 🔴 失败模式编码 (Failure Mechanism Encoding)

> 以下 19 条（SF-001~SF-019）是协议签名逆向中的高频失败路径。任何签名逆向任务启动前必须过一遍。开工攻坚另过准则 §1 六项。

## 方法论级错误

### SF-001: 不要假设算法是已知加密变种 (🔴 最惨痛)
- **错误**: XHS x-mini-sig 假设是 HMAC 变种 → 50+ 组合爆破全败
- **正确**: 算法是 GF(2^8) flattened transform + SHA-256 canonical tail
- **规则**: 先搜标准加密常量 (AES S-box / SHA K表 / HMAC魔数)；搜不到 → 大概率自定义变换，走反汇编+算子提取
- **成本**: 浪费一整天

### SF-002: 从顶层往下分析，不要从底层往上
- **错误**: 头条 APP — 从 SSL → Cronet → HTTP/2 frames (700行 Frida JS + RFC 7541 HPACK实现)
- **正确**: 88行 Java Retrofit interceptor → 一条语句截获所有请求
- **规则**: 先 Java 层 → 再 Native 层；底层超过 4 层未果 → 切顶层重新分析

### SF-003: 搜不到常量 ≠ 算法不存在
- **错误**: XHS 9.11.0 搜不到 GF 矩阵字面 → 误判"不用 GF(2^8)"
- **正确**: 矩阵乘法被 flatten 成散落的算子序列
- **规则**: 常量可能被 XOR 混淆存储 / 运行时动态计算 / 展开为算术序列

### SF-004: 服务端拒绝不一定是加密问题
- **错误**: 连信 sendsms resultCode:2 → 反复调试加密
- **正确**: 明文请求也返回 resultCode:2 → 是业务层拦截 (IP封禁/WAF/前置接口缺失)
- **规则**: 先发一个明文/空 body 请求确认错误码是否与加密有关

## 技术级错误

### SF-005: Unicorn RDTSC 选错分支
- **错误**: Apple Music CFF dispatch 依赖 `RDTSC % 3` → Unicorn 模拟值不同 → 状态错位 → 崩溃
- **规则**: Unicorn 模拟前必须先搜索 RDTSC/RDTSCP/CNTVCT_EL0/gettimeofday/clock_gettime

### SF-006: opaque token 不是内存指针
- **错误**: Apple Music SAP handle `0x1f2a04f6aec30` 当内存地址解引用 → 崩溃
- **正确**: CFF lookup table 的索引 token (非规范地址)
- **规则**: 地址值"不对" → 先验证是否可读，不可读就是 token

### SF-007: 加固 SO 的加密函数可能被 wrapper 处理
- **错误**: 连信 BangBang SO j_AES_ecb_encrypt → 逆向出调用链 → 加密结果与真机不一致
- **规则**: 加固 SO 逆向完成后必须抓真机包对比验证

### SF-008: 不要穷举超过 10 个算法假设
- **错误**: 50+ HMAC 组合爆破浪费一整天
- **规则**: 10 个组合失败 → 方向错了 → 切换到反汇编+算子提取路径

### SF-009: 跨设备复用密钥
- **错误**: XHS KEY64 从旧设备复制 → 全链路 406
- **规则**: 设备级密钥 (KEY64/seed64/device_id) 换设备必须重提

### SF-010: Frida send() 比文件写入更可靠
- **错误**: Apple Music FileWriter 在设备写 dump 数据频繁失败
- **正确**: send() 通道传 JSON → PC 端 Python 接收
- **规则**: 大量数据从设备传出 → 优先用 send()

### SF-011: APK 可能是 malformed
- **错误**: jadx 打不开 → 判断"加固了"
- **正确**: 3000+ malware 用 malformation 使工具崩溃 → 用 Malfixer 修复
- **规则**: jadx 打不开 → 先用 Malfixer 修复 → 再试

### SF-012: 验证前不说"算法还原了"
- **错误**: 签名字节级验证未做就说"完成了"
- **规则**: 100+ 组随机输入 SO vs Python 字节级一致 → 才说"算法还原了"

### SF-013: 签名与会话/请求序列生命周期绑定 → 纯离线不可行 (🔴 高价值止损)
- **错误**: 淘宝闪购 MTOP 真机 SG 重签（真 getSecurityFactors + 设备时间 + 新会话头，签名输入按反编译还原）被判 `FAIL_SYS_ILEGEL_SIGN`；而 verbatim 重放 App 原签名 = SUCCESS
- **正确**: `x-sign`/`x-mini-wua`/`x-sgext` 绑设备请求序列/会话内部态，服务端按序列校验 → 任何旁路/乱序签名非法；**unidbg 模拟同 SO 也被拒**
- **规则**: 若 `verbatim重放=SUCCESS` 且 `离线/oracle重签=ILEGEL_SIGN` 且 t/过期已排除 → **停纯算**，转策略 G 在线兜底（hook 抓 App 合法签名流量解析）
- **成本**: 不止损会在 unidbg/纯算上烧数天

### SF-014: unidbg/模拟器可能"跑通"但执行错误 → 无效 oracle
- **错误**: ct_client e9hgat5k，unidbg 错算自定义 AES → 产错密文；函数地址/算法形态都"逆出"了却无法字节验证
- **铁证识别**: AES-CTR keystream 若整条恒定重复（每块相同）= 执行坏了（真 CTR 每块必不同；本案输出了轮密钥缓冲 RK 而非 AES(counter)）
- **规则**: unidbg-as-oracle 前先验执行正确性（已知向量对拍）；执行坏则 byte-exact 受阻 → 转真机 root 内存 dump（token 生成时 dump 中间量）或长度对拍
- **成本**: 误判"已解"会无限投入

### SF-015: 三路验证全断 = 认栽信号（可靠静态 ≠ 可验证生成器）
- **触发**: ① unidbg 执行坏(SF-014) ② 真机 Frida 被反检测挡（爱加密级）③ 无服务端私钥 三条全断
- **规则**: byte-exact 需"正确执行的参考"；三路全断时，可靠成果（算法/明文/key/地址）≠ 可验证生成器 → 止损 = 长度对拍交付，或真机当 oracle 直接产值（若能绕反检测）

### SF-016: 目标进程从 frida 进程表反枚举消失 → 按名 attach 失败但进程活着
- **错误**: dy 抖音 MS SDK 运行一段时间后 `dev.get_process(pkg)` 报 `ProcessNotFoundError`，`enumerate_processes()` 189 个进程里唯独没有目标；误判"App 死了/被检测杀"
- **正确**: `adb shell pidof <pkg>` 拿真实 pid（adb 视角正常）→ `dev.attach(pid)` 直连成功；同一 App 反检测监控（metasec 275208 区）只藏枚举不藏 pid
- **规则**: frida 枚举失败 ≠ 进程死亡；先 adb pidof 确认，再 attach(pid)。RPC oracle 采集器应内置 pidof 回退
- **成本**: 误判会反复重启 App/误杀可用的 oracle 窗口

### SF-017: 批内快速采样制造"固定计数轮换"假象 → 轮换周期必须慢速/间隔实验判定
- **错误**: dy X-Gorgon 上下文批内（μs 间隔）切换点整齐落在 idx 0→1、10→11 → 误判"每 10 次签名轮换"；25 次慢速（100ms 往返）实验切换点变 3,6,13,17,23 不规则；sleep 控制实验（0.1s 不切/0.25s 切/0.4s 不切）才定性 **~0.5-0.6s 时间轮换（App 后台活动驱动）**
- **规则**: 任何"每 N 次轮换"结论若只来自批内采样 → 用变间隔重复实验交叉验证；时间驱动与计数驱动在慢速/间隔实验下表现截然不同
- **成本**: 错判轮换机制会误导密钥恢复方向（白烧数小时）

### SF-018: oracle 重放改造 body 字段触雷 → 服务器按语义绑定校验，改造优先级 query > body
- **错误**: dy 评论翻页想改 body `session_show_cids` 追加 cid（试过真 cid、假 cid）→ 服务器全部 -99999；一度怀疑签名/加密问题
- **正确**: query 的 cursor 可任意改 + oracle 重签 = 翻页成功（B 模式）；body 只可字节级原样（zstd 重压缩同语义无碍 → 服务器校验**语义**不校验字节流）
- **规则**: oracle 重放要改请求时，先跑隔离实验定位"哪个层可改"（E1 原样对照 → E2 重压缩改字节流 → E3 改语义），body 字段（cid 列表等）疑似会话状态绑定 → 语义不动是底线，要改就从 query 改
- **成本**: 每条错误路径半天起；错方向会怀疑到签名头上

### SF-019: 别把"业务参数"默认当签名/校验必需 → 增量砍参数实验验证
- **错误**: dy list 冷启动 -99999，长期怀疑 query 的 7 个"视频专属参数"（aweme_author/authentication_token/top_query_word/common_flags 等）必须与 aweme_id 匹配
- **正确**: 实验 A 一次砍掉全部 7 个参数 + 换 aweme_id → oracle 照签八神、服务器 status=0 照回评论 → 换视频 = 只改 aweme_id
- **规则**: "参数不可改"分两层独立验证：① 签名引擎接不接受（oracle 返回八神头还是 X-Neptune -8 最小签名分支）② 服务器业务侧认不认（status_code）；③ 用增量砍参数/单参数替换实验判定，不要靠猜
- **成本**: 冷启动弯路数小时；参数错判会误导整个改造方向

---

# 🚨 签名逆向高风险行动黑名单

1. **禁止** 在找到标准加密常量前就假设算法类型 (SF-001)
2. **禁止** HMAC/算法爆破超过 10 个组合 (SF-008)
3. **禁止** Unicorn 模拟前不检查 RDTSC/反模拟检测 (SF-005)
4. **禁止** 不验证字节级一致就说"还原了" (SF-012)
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

---

# 🧰 工具与版本时效性黑名单（2026-08-24 真机基线同步）

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

---

## Phase 1：6 路并行情报采集

> 🔴 **CHECKPOINT**: 启动 6 路采集前，先确认: SO 文件已获取? 真机/模拟器已连接? mitmproxy/ecapture 已配置? 搜过 GitHub 同类逆向了吗?

> 受女娲.skill Phase 1（6 Agent Swarm）启发。根据实际情况选择可用路径。

```
                  用户输入"逆向 X APP 的签名"
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                  ▼
   [有SO文件]         [有真机设备]        [开源参考]
        │                 │                  │
   ┌────┴────┐      ┌────┴────┐        ┌────┴────┐
   路1:SO静态  路2:IDA   路3:抓包  路4:Frida  路5:文献  路6:GitHub
   字符串搜索 深度分析  mitmproxy  Hook参数  Google   同类APP
```

### 路1: SO 静态分析（字符串 + 常量）

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

**搜索不到常量 ≠ 不是这些算法**。常量可能：
- 被 XOR 混淆存储
- 运行时动态计算（从多项式中即时生成）
- 被展开为算术序列（GF 矩阵 → flattened op list）

### 路2: 动态抓包

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

### 路3: Frida Hook 参数定位

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

### 路4: Unicorn 模拟（条件性使用）

**⚠️ 先检查反模拟检测**：
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
- 方案 C：放弃 Unicorn → Frida RPC

**如果无反模拟检测**：
```python
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM
# 加载 SO segments → 初始化堆栈 → Hook 关键调用 → 执行
```

### 路5: 文献 + Google 搜索

```
搜索策略：
- "<APP名> signature algorithm reverse"
- "<SO文件名> analysis"  
- "github <APP名> shield/sign algorithm"
- "<APP名> API protocol reverse engineering"
```

### 路6: 开源参考实现

| APP | 算法 | GitHub 参考 |
|-----|------|-------------|
| XHS Shield | white-box AES+MD5+RC4 | RedNote/Xiaohongshu-Shield-Algorithm |
| GeeTest | AES+RSA | 多个 Python 实现 |
| FairPlay | ECDH+HMAC-SHA256 | 学术论文（协议级） |
| 通用 MTOP | HMAC-MD5 | 阿里 MTOP SDK 开源版 |

---

## Phase 2：假设生成与验证

> 🔴 **CHECKPOINT**: 在生成假设前先跑 SF-008 检查 — 已尝试了多少个算法假设? 超过 10 个 → 🛑 **STOP**，不要继续生成假设，切换到反汇编+算子提取路径。

### 2.1 假设模板

基于已有经验自动生成 3 个竞争假设：

```
假设1: 标准加密算法（HMAC-SHA256 / AES-CBC / RSA签名）
  → 证据：找到标准常量、标准输出长度

假设2: 标准算法变种（改变 padding/IV/迭代次数）
  → 证据：输出长度标准但内容不匹配

假设3: 自定义算法（GF变换 / 私有密码学）
  → 证据：无标准常量、输出无规律、SO 内有大型状态机
```

### 2.2 三重验证协议

**验证 1: 输入输出一致性**
```
Python(已知输入) → 算法候选 → output_A
SO(已知输入)      → native call → output_B
assert output_A == output_B  # 字节级
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

---

## Phase 3：算法还原策略选择器

> 🔴 **CHECKPOINT**: 策略选择前必须确认: SO 搜索过标准加密常量了? Unicorn 前检查过 RDTSC? 反模拟检测评估完成? 选择策略后 🛑 **STOP** — 展示策略选择理由给用户确认，再执行。

```
SO 分析结果 + 假设验证结果
        │
        ▼
┌───────────────────────────────────────────────────────┐
│  找到了标准加密常量 (AES S-box / SHA K表 / HMAC魔数)  │
│  → 策略 A: 已知算法重写                                │
│  → 案例: Bilibili GeeTest w = AES-128-CBC + RSA       │
│  → 工时: 数小时-1天                                    │
├───────────────────────────────────────────────────────┤
│  CFF 混淆 + D-810 unflattener 仍然有效                 │
│  → 策略 B: D-810 unflatten → 算法追踪 → 算法重写       │
│  → 工时: 1-3天                                         │
├───────────────────────────────────────────────────────┤
│  CFF 重度混淆 + D-810 无效 + SO 只读常量依赖            │
│  → 策略 C: Frozen Blob 提取                             │
│  → 案例: XHS libtiny (546B 替代 7.95MB SO, 8.5x 加速)  │
│  → 工时: 半天-1天                                       │
├───────────────────────────────────────────────────────┤
│  定制代码虚拟化 + 200+ handler + 跳转表                  │
│  → 策略 D: Frida 会话提取 → 离线签名                    │
│  → 案例: Apple Music SAP (send() 方案)                  │
│  → 工时: 1-2天                                          │
├───────────────────────────────────────────────────────┤
│  反模拟检测 (RDTSC/时间) + 不复杂 SO                     │
│  → 策略 E: Frida RPC 在线签名                            │
│  → 案例: Apple Music Unicorn 受阻后的备选               │
│  → 工时: 半天                                            │
├───────────────────────────────────────────────────────┤
│  GF(2^8) 字节变换 (无标准常量)                           │
│  → 策略 F: IDA 反汇编 + 算子序列提取 → frozen op list   │
│  → 案例: XHS x-mini-sig (50+ HMAC 爆破失败后的正解)     │
│  → 工时: 2-4天                                           │
├───────────────────────────────────────────────────────┤
│  RSA-PKCS1随机填充 / 混合加密(含 rand 会话密钥)          │
│  密文每次不同 → 放弃逐字节                                │
│  → 策略 RSA: hook 加密原语入参验证确定明文 / 长度结构对拍│
│  → 案例: ct_client loginAuthCipher / e9hgat5k / 连信 CKey│
│  → 工时: 1-2天                                           │
├───────────────────────────────────────────────────────┤
│  签名与会话/请求序列生命周期绑定 (重签 ILEGEL_SIGN)      │
│  → 策略 G: 在线兜底 (hook 抓 App 合法签名流量 → 解析)    │
│  → 案例: 淘宝闪购/me.ele MTOP (verbatim 重放 OK)         │
│  → 工时: 半天-1天    | 判定见 SF-013                     │
├───────────────────────────────────────────────────────┤
│  裸 HTTPS/QUIC 协商失败，原版 App 同环境能通              │
│  → 策略 H: 传输复刻 (fp_stack 真机 CH + 私有 QUIC 版本)  │
│  → 案例: 盒马搜索 H1 / 猫眼 yanchu H1 / ele draft-29     │
│  → 工时: 档案已有则小时级 | 判定见 SF-016                 │
└───────────────────────────────────────────────────────┘
```

> **假设结论 → 策略连线**（Phase 2 产出直接路由；多条件同时命中按 first-match 从上到下裁决）：
> 假设1 标准算法 → 策略 A（重写）/ RSA（随机填充类）；假设2 标准变种 → 策略 A + KEY/IV/padding 枚举对拍（Phase 4.3）；
> 假设3 自定义/无常量 → 按形态路由：CFF（D-810 有效→B；D-810 无效+只读常量→C）、重度虚拟化 200+ handler→D、GF(2^8)→F、VMP→H；
> 生命周期绑定证据（SF-013 三判据）→ 直接跳 G，不再进假设循环；
> 反模拟检测（SF-005）阻断 Unicorn 时 → 策略 E（Frida RPC 在线签名；重度虚拟化 SO 主选 D，Unicorn 受阻后备选 E）。
>
> **D vs H 判定**：静态形态重叠（都有 handler 分发）时看"轮换"——运行期多次采样同一输入，
> 输出/上下文随时间变化（SF-017 慢速/间隔实验定性）→ H；不变 → D。可先按 D 会话提取，
> 发现轮换证据即升级 H。反 hook checksum（SF-016 区 275064 类）不改变策略选择，只决定注入对抗手段。

> **oracle 到手后要改请求？先跑 SF-018 隔离实验阶梯**（第1步 原样对照 → 第2步 重压缩改字节流 → 第3步 改语义）
> 定位"哪个层可改"：query 可改（cursor/count + 重签）→ body 语义不可动。参数必需性按 SF-019 分两层验证
> （签名引擎出不出八神 vs 服务端 status_code），增量砍参数实验，不要靠猜。

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
6. 验证：100+ 随机输入 SO vs Blob 字节级一致
```

### 4.2 GF(2^8) Op List 方法（策略 F）

```
步骤:
1. IDA 反汇编签名函数 → 识别所有 GF(2^8) 算子
   (madd/umull/eor/and/orr/ubfx/bfi/lsl/lsr/extr 组合)
2. 按执行顺序序列化算子 → JSON ops list
3. Python lift: 每条算子 → 对应的 Python int/numpy 操作
4. 验证：已知输入 → Python output == 真机 output（字节级）
```

### 4.3 标准算法重写（策略 A）

```python
# 确认以下参数后直接使用标准库：
import hashlib, hmac
from Crypto.Cipher import AES

# 验证 KEY/IV/padding/mode 与真机一致
# 验证至少 100 组随机输入
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
  └─ fp_stack: 传输墙先过再谈签名（SF-016）
```
### AI 驱动案例速查

#### Case A: JavDB — 全自主逆向 (7 messages, <5 min human time)
- AI 自主: 反编译 APK → 提取 124 个 API → 逆向 ARM64 `jdsignature` → 派生 native key generation (APK signing cert DER bytes)
- 产出: 5,422 行 OpenAPI spec + Python SDK
- 关键: AI 读了 ~3000 行 ARM64 汇编,无人类逆向经验介入

#### Case B: 头条 APP — 15+ iterations 才找到正路
- ❌ 尝试: SSL hooking → Cronet native → HTTP/2 frame parser (700行 JS in Frida, RFC 7541 HPACK+Huffman!)
- ✅ 最终: 88 行 Java Retrofit interceptor Hook → 一条语句截获所有请求
- **教训 F-017**: 从顶层往下,不要从底层往上

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

## Phase 5：验证与文档

> 🛑 **STOP**: 这是最终验证关卡。100+ 组随机输入字节级一致通过 → 才能说"算法还原了"。SF-012 铁律：未验证不说完成。

### 5.1 字节级验证（强制）

```python
# 100+ 组随机输入验证
for i in range(100):
    random_input = os.urandom(32)
    py_output = pure_python_sign(random_input)
    so_output = call_so_sign(random_input)  # 或抓包对比
    assert py_output == so_output, f"Mismatch at iteration {i}"
    # → 全部通过 = 算法完全还原
```

### 5.2 端到端验证

```python
# 完整请求验证
headers = build_headers(url, method, body, params)
response = requests.get(url, headers=headers)
assert response.status_code == 200
assert response.json()["code"] == 0
```

### 5.3 产出文档模板

```markdown
## [APP名] [签名名] 逆向完成

- 算法: [准确描述]
- 输入: [格式 + 示例]
- 输出: [格式 + 长度]
- 密钥: [来源 / 固定值 / 设备绑定]
- 有状态: [是/否]
- 跨版本稳定性: [已验证/未验证]
- 纯算实现: [文件路径]
- 性能: [N requests/s]
- 验证: [N/N 随机输入字节一致]
```

---

## 案例速查

### XHS x-mini-sig
```
算法: GF(2^8) flattened transform + SHA-256 canonical tail
策略: F (op list 提取)
错误: 50+ HMAC 爆破失败
教训: F-002 — 不要假设是已知加密变种
文件: projects/xhs_apk/analysis/xmini_headers/xmini_sig_pure.py
```

### XHS Shield  
```
算法: 白盒 AES → 变种 MD5 → RC4 变种 → Base64
策略: A (已有开源参考)
跨版本: 稳定 (9.11.0 → 9.18.0 仍可用)
文件: xhs_pure_protocol/shield_ref/shield_sdk.py
```

### Apple Music X-Apple-ActionSignature
```
算法: FairPlay SAP (ECDH + HMAC-SHA256 + AES-CTR)
策略: D (Frida 会话提取, CFF 200+ handler 无法静态还原)
SO: x86_64 (MuMu), ARM64 (真机)
文件: projects/applemusic/x_apple_action_signature/
```

### Bilibili GeeTest w
```
算法: 自定义 Base64 + AES-128-CBC + RSA PKCS1v15
策略: A (标准算法组合)
验证: Python vs Node.js 字节一致
文件: projects/appbilibili/geetest/w_generator.py
```

### ct_client（爱加密/电信）— 多签名族
```
getLoginRandomCode (SMS发码): 明文JSON信封(Retrofit @k7.c 无 @k7.a → isReqEnc=false, 无整体3DES/无签名头)
  + 字段级凯撒+2(仅 phoneNum/androidId)。策略: 抓包+注解判加密层; 别碰天翼{p,k}一键登录SDK弯路。
  验证: 字节级 2/2。文件: projects/ct_client/scripts/ct_getrandomcode.py
滑块发短信 (纯算端到端, 无设备/Frida): 取滑块图→CV解缺口→verificationSliderPicture(g.t)→signSignatureString(服务端下发)→smsId
  g.t(v,extra)=Base64(AES/ECB/PKCS5(v, key=Base64.decode(extra))); 32B key=AES-256
  distance=gap_x/(0.848*bg_w)["ui"模式]; 轨迹"x#y#t"加速S曲线+overshoot。文件: projects/ct_client/scripts/ct_slider.py
loginAuthCipher (userLoginNormal登录体): PT(64B)=各字段右填'$'(0x24)到固定宽拼接(无分隔符)
  → RSA_public_encrypt(PT, strPublicKey1, RSA_PKCS1_PADDING) → 128B → base64(~172字符)
  策略: RSA(明文64B确定→hook RSA_public_encrypt 入参核对; 密文每次随机不可逐字节)。文件: loginAuthCipher_gen.py
e9hgat5k (msec libmsec.so 防爬token): base64url(RSA_blob[260B]) + ".." + base64url(AES_ct[829B]) [+ "." + suffix]
  RSA-1024(E=65537, N=c190b4f5..62137f83, 真机堆dump提取)包裹会话密钥; AES_ct=设备指纹JSON的AES-256密文
  策略: 长度/结构对拍(会话密钥rand+无server私钥)。★ unidbg 错算AES见 SF-014。文件: e9hgat5k_gen.py
```

### 连信（掌信 v8.6.901.1，libzhangxin 梆梆）
```
sendsms 信封加密: Content-CKey=RSA/ECB/PKCS1(16随机小写字母, pub1@0x1860AE 2048bit/e=65537) → 256B → hex(512字符)
  body=AES/ECB/PKCS5(json_utf8, key=同那16字节CKey直接当key); 头 Content-CKey-Version=12, Content-Encrypted-ZX=1
  ★坑: org.json.JSONObject.toString() 把 '/' 转义 '\/'(python json.dumps 不转); 字段真实顺序+hashKey末尾+紧凑无空格
  hashKey=固定常量MD5(疑APK完整性, 与body无关)。策略: C(梆梆内存dump脱壳, 见 android-unpack)+静态
  验证: 全链路Frida-oracle字节级一致。文件: projects/lianxin_apk/src/lx_crypto.py
```

### 淘宝闪购 / me.ele MTOP（★生命周期绑定止损案例）
```
签名输入(已全还原): data="<appkey>"&md5hex_lower(body|query)&t → IUnifiedSecurityComponent.getSecurityFactors(...)
  → {x-sign,x-mini-wua,x-sgext,x-umt}(URLEncoded)。IUnifiedSecurityComponent = 动态代理 $ProxyN(每次号变)
  网关 getSecurityFactors 仅冷启 homefeed 拉取触发; spawn 模式 Java.perform 回调不执行(Atlas延迟)
策略: ★G 在线兜底 —— verbatim重放App原签名=SUCCESS, 旁路/真机SG重签=FAIL_SYS_ILEGEL_SIGN(绑会话序列, SF-013)
  纯离线不可行 → hook libxquic 抓App合法签名流量 → 解析。文件: projects/taobao_shangou/{mtop_capture.js,collect_live.py}
魔改frida-server进程名乱码: 按名 attach 失败 → 用 enumerate_applications().identifier=="me.ele" 取 pid
```

### 抖音 38.0.0 八神签名（libmetasec_ml.so = 字节跳动 MS SDK，★VMP+轮换密钥案例）
```
入口: libsscronet 47A31C → metasec+0x28065c 回调 char*(url,headers)→"name\r\nvalue\r\n..." 串
  (内部: 264E3C 签名主函数(加密函数指针) → 274C60 VMP interp(⚠️275064区 syscall包装+0x312768B checksum反hook勿hook) → 2810d4 dispatcher)
八神结构(112组RPC差分+SF-012字节级验证):
  X-Argus  = base64(LE32(unix_ts))  ★完全破解, 12/12跨秒+8/8历史全吻合
  X-Khronos = 同源 ts 十进制 (metasec 内部缓存时钟, RPC 空闲期间按批推进)
  X-Gorgon = 8404 + ctx2B(高位偶数化) + 0001 + [4B keyed-hash(query) + 1B ctx + 13B ctx-token]
    ★输入=query字符串 (path/scheme/fragment/headers 全部排除; 与静态 strchr('?'/'#') 提取器互证)
    ★ctx ~0.5-0.6s 轮换(App后台活动驱动) → 离线不可复现; 4B≠md5/crc32=keyed hash
  X-Medusa = LE32(内部ts) + ~910B 疑似 AES-GCM payload(尾16B tag)
  X-Ladon  = 4B (第4字节=ctx线性分量, 第3字节含签名计数器奇偶交替)
  X-Helios = 36B 全输入敏感; X-Neptune=短URL单独输出(-8|...最小签名)
策略: ★H 在线 oracle (VMP核心+轮换密钥 → 纯算死路) — App运行 + Frida RPC 直调 28065c 即签名服务
坑: ① App 运行后从 frida 进程表反枚举消失 → adb pidof 直连 attach(pid)
    ② frida 16.5.7 RPC 方法名必须全小写(Python绑定 lower() 查找, camelCase 报 unable to find method)
    ③ 空 url RPC 返回 NULL 不崩; RPC 线程上 Khronos 滞后真实时间
文件: projects/dy/{hooks/dy_hook21.js,scripts/dy_oracle_collect.py,capture/oracle_dataset.json,docs/signature_structure.md}

★oracle 重放改造边界（2026-08-27 评论接口 /aweme/v2/comment/list/ 实证, 见 SF-018/019）
  ① body 语义绑定: session_show_cids 与客户端会话状态绑定校验(改真/假 cid 均 -99999)
     zstd 重压缩同语义无碍 → body 只可字节级原样, 要改从 query 改
  ② query 自由: cursor/count 可改 + oracle 重签照过(翻页 B 模式); count 服务器 cap ~50; 其余参数照抄模板
  ③ ★minimal query 换视频: 7 个视频专属参数(aweme_author/authentication_token/top_query_word/
     common_flags/current_l1_comment_count/comment_count/is_fold_list)全砍 + 只改 aweme_id → 照签照回
     (status=0 已验证; 返回评论归属以实跑第1页 [归属] 行确认为准)
  ④ 响应解析: hex 前缀("\xa8"等) + \n\n + JSON → find(b"{") + raw_decode;
     accept-encoding 必须 gzip, deflate, br(不声明 ttzip, 否则响应是 ttzip 需手动解)
  ⑤ IPv4 强制: PC DNS 把 api5-core-lf.amemv.com 解析到 IPv6 直连挂起 → socket.getaddrinfo monkey-patch 只留 IPv4（滤掉 IPv6）
  ⑥ 签名引擎 vs 服务端两层: 简化 URL(砍 query 参数) oracle 返回 X-Neptune -8 最小签名分支(不是八神)
     但含完整 query 的任意 URL 都能签 → 服务端对砍掉的业务参数不校验(两层分开验证, SF-019)
文件: projects/dy/scripts/comment_replay.py (--aweme-id 换视频 / --from-charles 抓模板 / paging B 模式)
     projects/dy/docs/comment_replay_usage.md (换视频两方法 + 翻页机制表 + 已知限制)
```

### 瑞幸 q/sign + 同盾 blackBox
```
q/sign (liblka-secure，干净导出非加壳):
  getKey4LK = AES128-ECB(urlsafe-b64(rawSecret), key="Safe_box_1234567")
  派生 key = NxtPlpL70ssMD8is
  q = b64url(AES128-ECB-PKCS7(paramsJSON, key16))  // ECB→q 前缀恒定
  sign = concat(abs(int32_BE(md5("cid=;q=;uid="+key)[k:k+4])) for k in 0,4,8,12)
  策略 A。e2e: 新 q/sign → capi.lkcoffee.com order/preview HTTP 200/code=1
  文件: projects/luckin/scripts/lka_gen.py
blackBox (同盾): ★真值=26 字符，不是 3000B blob（那是数美）。
  blackBox = LEAD + reverse(td-tid_content)[1:] ，pos 4/15/24 插 3 个 base62
  td-tid 在 shared_prefs/fm_shared.xml；chk 丢弃。策略 A。preview 不校验 blackBox≠过风控
  文件: projects/luckin/scripts/bb_gen.py
教训: 主攻点选对（自研干净 SO）远胜死磕 360 壳/同盾 native
```

### Keeta / 猫眼 mtgsig（美团系）
```
mtgsig = 请求无关设备令牌（非 TEE）：改 body/path 后 a5/a7/a8/a9 不变，仅 a2 变
Keeta Shepherd s-ca-signature = HMAC-SHA256(appSecret, canonical) 纯算通
  纯算 mtgsig 两墙：MD5 白盒 + unidbg 缺 base.apk 资产曾 errno 512（挂裁剪 apk 后可产真令牌）
  传输: Shark 隧道 / libcronet；裸 HTTPS 边缘 403。混合 e2e（离线 body + 设备隧道）code=0
  禁刷无效令牌 → 设备 #41SR 软封（原版 App 也 403）
猫眼: key36[i]=source[i]⊕appKey[i]⊕a10_mask ；source 设备稳定
  a2 纯算 + fp_stack H1 → yanchu project/detail HTTP 200 success（止损：单次只读，勿再刷）
  入口: projects/maoyan/scripts/pure_mtgsig.py + fpstack_client.py
```

### 盒马搜索（止损型）
```
判官: mtop.wdk.search.suggest HTTP 200 SUCCESS + 非空联想
形态: 活机 buildRequestHeaders 全头 + fp_stack H1 verbatim（四头=时效炸弹，非纯算）
入口: projects/freshippo/scripts/search_client.py replay
谱: projects/freshippo/docs/SEARCH_PROTOCOL.md
禁止宣称四头纯算；禁止再刷同一条。search.item / az95 另开
```

### Play login v2 / MinuteMaid DG
```
已解: DG 程序常数 #1/#123/#266 字节级，bytecode=53993
卡点: #2 sealed env（本地 vs live 213 族每块差字段）；MI613e 仍 gf.uicd
形态: 部分解析 + #2 止损。权威 projects/play_login_v2/docs/LOCAL_CLIENT.md
禁止重复无效 POST（同 token 烧号）
```

---

## 🚨 高风险行动黑名单（与上方 14 条合并，此处不重复）

交付前过准则 §5 四件套（谱×物×证×界）。假设不配作为交付物。

> 已并入文首「🚨 签名逆向高风险行动黑名单」（14 条，含 SF-001~SF-019 映射）。此处保留节名仅为历史锚点。

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

### 6.1 unidbg 工程化交付：SO 参数生成逻辑 → jar → Python / MCP

> 凡是从 SO 里产出的值——**签名 / 设备指纹(fp_stack/blackBox) / 防爬 token(e9hgat5k/mtgsig/CKey)
> / 加密参数 / 密钥派生**——只要 SO 已能在 unidbg 补环境跑通，就**不重写算法**，直接 jar 化交付，
> 省去纯算重写工时与后续每次生成的 token 消耗。

🔴 **打包前置门槛（硬约束，先 Java 验证 → 再打 jar）**：
1. 在 unidbg 工程里写 `main()` 验证：加载目标 so → 跑 JNI_OnLoad/RegisterNatives → 按崩溃点补环境 → 生成参数
2. 与真机/抓包样本**字节级对拍**（SF-012）；不一致 = 补环境还没成，**禁止打 jar**
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

---

## 自进化机制

- 每次成功逆向新签名 → 追加到案例速查
- 每次发现新失败原因 → 追加到假设模板
- 每次验证新策略有效 → 更新策略选择器

进化触发词：`记录签名逆向` / `更新算法案例`

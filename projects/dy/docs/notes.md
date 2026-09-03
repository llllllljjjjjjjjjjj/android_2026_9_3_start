# 八神签名链分析笔记（持续更新）

## 2026-08-24 动态抓取进展

### 1. libsscronet.so 请求头构建链（已理清）

```
URLRequest 对象 X19 (=4127ac 的 x0 参数)
├─ [X19+8]+0x70   头容器 (元素 0x30B = {name:std::string, value:std::string})
├─ X19+0x1E0      子对象 X20 (优化参数来源)
├─ X19+0x358      头写入目标 X21 (=X19+0x358 处对象)
├─ X19+0x7A0/0x7A4  32 位字段（每次调用同值，疑似请求相关长度/ID）
└─ X19+0x7AC      标志字节（sub_493510 的 W3 参数）

4127ac 流程（"删除旧签名头"）：
1. 栈槽表 SP+0x1A0 (35×0x18 std::string) 赋头名:
   0x288=x-ss-dp 0x2A0=x-tt-bypass-dp 0x2B8=x-ss-req-ticket
   0x2D0=x-vc-bdturing-sdk-version 0x2E8=x-khronos 0x300=x-gorgon
   0x318=x-ladon 0x330=x-tython 0x348=x-argus
2. sub_226F08 构造容器视图
3. 循环 sub_37F078(X21, {头名,len}) —— 从 X21 容器删除该头到末尾
4. 循环 sub_204CC0(槽) —— ★实为 std::string 析构器 (SSO 直接 RET, 长模式 free)
5. 清理
```

### 2. 关键函数语义（IDA 实证）

| 地址 | 语义 | 证据 |
|------|------|------|
| 0x204CC0 | **std::string 析构器**（6 条指令: LDRSB [X0+0x17] TBNZ bit31 → free） | 全函数 dump |
| 0x37F078 | **EraseFrom(obj, {name,len})**：容器中删 name 起元素到末尾（元素 0x30B 双 std::string） | 0x37f0c4 块 SDIV/MADD 0x30 + sub_1F159C×2 |
| 0x37ED64 | **SetHeader(obj, key{ptr,len}, value{ptr,len})**：查→更新/追加（"invalid key" 日志串） | 0x37ed98 LDP X0,X1,[X1] + sub_37ECF0 查找 + sub_20ABD8 赋值 |
| 0x37ECF0 | FindHeader(obj, key) → 位置/end | 被 37F078/37ED64 共用 |
| 0x493510 | 生成双输出字符串（→ x-common-params-v2 等），读全局单例 [X0+0xC78/0xCB0/0xCC8/0xC80/0xC88/0xD18] | 0x412c90 调用点 |
| 0x4127ac | 头构建主函数（226 次/240s 实测） | hook4 |

### 3. Java native 门 ms.bd.c.y2.a(id, sub, flag, str, obj) id 编码

| id | 族 | 含义（动态实测） |
|----|----|----------------|
| 16777217 0x01000001 | 0x01 解密 | 字符串解密原语（1618 次/150s） |
| 16777219 0x01000003 | 0x01 | 解密相关 |
| 33554445 0x0200000D | 0x02 签名 API | sub=3,2,1 递减轮询，返 Integer |
| 33554446/47/41/33 | 0x02 | flag=metasec 全局指针（0x7D17E00010=metasec+0x350010） |
| 50331651 0x03000003 | 0x03 查询 API | flag=metasec+0x384E60，返 Long（192 次/150s） |
| 67108865/66/68 0x040000xx | 0x04 SDK | 初始化/版本("1128")/状态 |
| 83886081 0x05000001 | 0x05 状态 | sub=268435459 |
| 150994945 0x09000001 | 0x09 特征 | — |
| 167772161/164 0x0A000001/4 | 0x0A 配置 | sub=选项值 |

### 4. 待验证假设

- x-argus/x-gorgon/x-ladon/x-khronos 的生成：4127ac 只**删**不生成 →
  生成在别处（metasec via Y2.a 0x02 族，或 sscronet 内其他函数）→
  **hook sub_37ED64 SetHeader 抓设置流**（hook5 进行中）
- x-common-params-v2 值 = sub_493510 输出（含公共加密参数）
- URL 在 X19 深层嵌套（直接扫 ±0x2000 无果）

### 5.1 神头注入路径追踪（2026-08-24 下午）

```
411e74 (URLRequest 回调, 字符串 '?#','_$')
  ├─ BL loc_3411B4(X21,X22,X20, 回调结构{ADR sub_4123FC@[X25+0x20]}) → W20
  ├─ W20 != -1 (成功) → BL sub_412680(X19, W20)
  │     └─ 412680 = Chromium MaybeStartTransactionInternal (字符串实证)
  │           └─ 4127a8: BL 4127ac (删旧头)
  └─ W20 == -1 (失败) → BL sub_4127AC(X19) (删旧头)

4127ac (删旧签名头, hook8 实测 LR=+411fb0 唯一调用点)
  ├─ X21 = X19+0x358 = 头容器 {begin@0, end@8}, 元素 0x30B = {name,value}
  │   (37F078: LDR X8,[X0] / LDR X23,[X0,#8] 实证)
  ├─ [X19+8]+0x70 = URL 容器 (hook7 实证第一元素=完整 URL)
  ├─ EraseFrom 删除: x-argus/x-gorgon/x-ladon/x-khronos/x-tython
  │   + x-ttnet-bypass-sandbox/x-ttnet-scene-type/x-ttnet-origin-url 等
  └─ 条件 SetHeader("smbyttnet","1") @412b8c

★ 神头字符串 xref: sscronet 全库仅 4127ac 一处引用 (ida_xref_strings.py)
  → 写回函数不在 sscronet 明文引用 → 上层(Java/metasec)通过
    魔改 Cronet API (如 j_Cronet_HttpHeader_Create) 设置
x-ss-stub 生成器 0x26d248: BL 0x5CDB28(X2,X3,out) → sub_32E6C4 → 
  j_Cronet_HttpHeader_Create("x-ss-stub", 值) — PACIASP 指针认证导出 API
x-ss-stub 值 = 32hex MD5, 每请求变化, 走 SetHeader(37ED64) 设置 (hook5c 实证)
```


### 5.2 ★神头写入函数已锁定（2026-08-24 hook11/hook12 时序实证）

hook11 三点时序对比（411e74 / 412680 / 4127ac 容器状态）决定性结论：

```
[411e74-E] #2 (no-gods)                    ← 进入 OnBeforeURLRequest: 容器空
[412680-E] X-Argus=QfOLag== X-Gorgon=...   ← MaybeStartTransactionInternal: 八神齐全!
[4127ac-E] 同值                            ← 删除前仍在
→ 写入窗口 = 411e74 之后、412680 之前 = 3411b4 的 BLR 虚调用内!
```

- x-ss-stub 在 411e74-E 已有（SetHeader 路径，更早阶段）→ 与八神写入路径分离
- 部分请求全程 no-gods（资源类请求不需要神头）
- 411e74 全量反汇编（ida_loc10）：
  - X20 = X19+0x358 头容器; X21 = [[X19+8]+0x40]+0x28 网络上下文对象
  - 查 force_tt_hpack_optimization / x-ttnet-scene-type → 有值则写 [X19+8]+0xF68
  - alloc 0x40 回调对象 {sub_415830, sub_20353C, sub_21B054}
  - BL loc_3411B4(X21=ctx, X22=内部对象, X20=容器, X3=回调结构)
  - W20 != -1 → BL sub_412680; == -1 → BL sub_4127AC(删头)
- 3411b4 (72B, IDA 误并入 3410a4): BLR [[X21]+0x18]
  - **神头写入函数 = 网络上下文对象 vtable+0x18 虚方法**
  - hook12: 3411dc onEnter 抓 X9=虚方法地址 + 容器 before/after → 确认
- 3410a4 邻函数 = NetworkDelegate::NotifyBeforeURLRequest (BLR vtable+0x10)
- 3411b4 的 xref 仅 40b168(409e7c)—— 411e74 的 BL 在 IDA 中未建 xref(分析遗漏)

调用者链(40b168 ← 409e7c)待 hook12 后确认;下一步:拿到写入函数地址 → IDA 反汇编
该虚方法 → 找八神生成器(预期调 libmetasec_ml.so 加密区)

### 5.2 待验证

- 4127ac 删除的旧神头从哪来 (X21 容器 onEnter 状态) → hook9 抓取中
- 新神头何时写回 X21 容器 → hook9 onLeave 对比
- 411f88 处 W20 成功/失败比例 → hook9

```
0x27e7f0 第一段: 一次性初始化 (LDAR/STLR dword_3E4DEC)
   └─ BL sub_168820(unk_A6888, unk_3E4DE4, unk_A68E4)  ← XOR 解密器 dst=a^b
末尾跳板: BL sub_27E874; ADD X1,X0,#0x34; BR X1
   └─ sub_27E874 = "返回地址 thunk": STP 把 X30(=返回地址)写栈, LDR 读回 → X0=0x27e86c
      → BR 0x27e86c+0x34 = 0x27e8a0 = 第二段 (函数分段混淆, IDA 函数边界是假的)
第二段: 重复模式 {保存X0-X7→BL thunk→+0x38跳转→恢复→BL sub_161A34}
   ├─ 0x27ee84: ADRP X25,#JNI_OnLoad_ptr; BL sub_2AD080(X22, &JNI_OnLoad, 4)
   │     = ★代码完整性自校验 (校验自己的 JNI_OnLoad, 反 tamper/反 hook)
   ├─ 0x27eee4: BLR X8 ([X19]vtable+0x30) — 疑似 RegisterNatives 间接调用
   └─ NZCV 花指令 (MRS/MSR NZCV) + 假 RET (ADR X6; MOV X30,X6; RET) 混杂
RegisterNatives 表: 静态不可见 (运行时解密+间接调用) → hook libart
   _ZN3art3JNI15RegisterNativesEP7_JNIEnvP7_jclassPK15JNINativeMethodi (hook7)
```

### 6. 工具链备注

- hook 脚本 console.log → python frida 默认直打 stdout（不是 on_message），
  run_hook.py 的 out.log 只含 runner 自己的 log
- 抖音冷启动 40-90s 不定，libsscronet 加载有延迟
- frida 16.5.7 + f1657 官方 server spawn 抖音未被检测（累计 10+ 次 240s 会话零崩溃）

### 5.3 神头写入函数定位成功 (hook15, 2026-08-24)

- **写入函数 = libsscronet.so+0x47a31c (sub_47A31C)**: hook15 抓到 vtable+0x18 运行时值
  - 反汇编: artifacts/ida_godfn_47a31c.txt
  - 链路: 411e74(OnBeforeURLRequest) → 3411b4 → BLR [ctx vtable+0x18] = 47A31C
- 函数性质: **不是八神生成器**, 是 sscronet 的 ttnet 流量控制入口 (0x47a31c-0x47af90, 3.2KB)
  - 处理头: x-ttnet-origin-url / x-ttnet-bypass-sandbox / x-metasec-bypass-ttnet-features
    / x-tt-oec-opaque-enable / x-metasec-bypass-mssdk / x-metasec-ttnet-native-drop
- **metasec 桥接 (核心发现)**:
  - 47aa9c: LDAR X23, [qword_5FFE80]  ← 全局回调指针
  - 47aaec: BLR X23(X0=str1, X1=str2) → 返回 char* 签名串
  - 47ab40: sub_2ED608(签名串, 分隔符",", mode=2, ...) → vector<{name,value}> (元素0x18)
  - 47abc4: 循环 sub_37ED64=SetHeader(容器, name, value) 写入
  - qword_5FFE80 写入者 = metasec 注册点 (待 ida_bridge.txt xrefs 确认)
- 相邻辅助: sub_47AF90 (1参 bool), sub_47B598/47B740 (多参组装), sub_47BA98 (返回 header 列表)
- hook16 动态抓取: 读 qword_5FFE80 值→定位 metasec 模块 + BLR X23 明文 + SetHeader 八神名值对
- iptables UDP443 双栈 REJECT 已清 (红线收尾)
- 附: hook15 事件#5 容器首见完整八神 (X-SS-STUB/X-Argus/X-Gorgon/X-Helios/X-Khronos/X-Ladon/X-Medusa)

### 5.4 metasec 回调定位成功 (hook16, 2026-08-24)

- **[PTR5FFE80] = libmetasec_ml.so+0x28065c** ← 八神生成回调 (全局函数指针 qword_5FFE80)
- 注册链: sub_26D220(SScronet 表条目, 0x5d5470 表指针) = setter (qword_5FFE80 = X1)
  - 第二回调 qword_5FFE78 = sub_26D234 setter (被 sub_47BA98 使用)
  - 调用者通过 0x5d5300+ 函数指针表寻址 (JNI 注册)
- **回调协议** (47A31C@47aaec / 47B598@47b638 / 47BA98@47bafc 三处同型):
  (char* str1, char* str2) → char* 返回串 → sub_2ED608(mode=2, 分隔符",") 解析
  → vector<{name,value}> (元素 0x18) → 循环 SetHeader(37ED64) 写入容器
- **hook16 抓取 102 组八神名值对** (SetHeader 写入瞬间):
  - X-Argus: 8 字符 base64 (6 字节) | X-Ladon: 8 字符 base64 (6 字节)
  - X-Gorgon: 52 字符 hex (26 字节, "8404" 开头) | X-Helios: 44 字符 base64 (33 字节)
  - X-Khronos: unix 秒级时间戳 | X-Medusa: 长 base64 (设备指纹相关)
  - X-SS-STUB: 32 字符 hex (MD5 链, 26d248 路径, 非 metasec)
- 47B598/47B740/47BA98 在八神路径中未被调 (b598=0/b740=0/ba98=0) — 仅 47A31C 主路径
- 47aaec (BLR X23 指令点) attach 失败 "unable to intercept" → 改 hook 47aae4/47aafc 或直接 hook metasec 回调
- 下一步: metasec+28065c 反汇编 (VMP 硬化, 预期入口 stub) + 抓 BLR 入参明文

### 5.5 算法还原完成（RPC oracle + 差分分析, 2026-08-24 定稿）

**完整结构文档: `docs/signature_structure.md`**；采集数据 `capture/oracle_dataset.json`（112 组）

- **RPC oracle 打通**: dy_hook21.js（纯 RPC, 无 Interceptor）+ dy_oracle_collect.py
  - 坑1: App 运行后从 frida 进程表**反枚举消失** → `adb shell pidof` 拿 pid 直连 attach(pid)
  - 坑2: frida 16.5.7 RPC 方法名必须**全小写**（Python 绑定 lower() 查找）
  - 坑3: 空 url 调用返回 NULL（App 不崩，28065c 内部有防御）
- **分支发现**: URL 无 query/过短 → 仅输出 `X-Neptune`（-8|... 最小签名，新发现的第 9 头）；合法 URL → 6 头
- **X-Argus = base64(LE32(unix_ts)) ★完全破解**: 8 历史点 + 12 跨秒点（SF-012）字节级全吻合
- **X-Gorgon 结构**: `8404`+ctx2B+`0001`+[4B keyed-hash(query)+1B ctx+13B ctx-token]
  - 输入=query（path/scheme/fragment/headers 全排除, 与静态 282020 strchr('?'/'#') 互证）
  - ctx ~0.5-0.6s 轮换（App 后台活动驱动, 非固定计数）；4B≠md5/crc32/sha256=keyed hash → 离线不可复现
- **X-Medusa**: LE32(内部ts)+~910B 疑似 AES-GCM（尾 16B tag）
- **X-Ladon**: 第 4 字节=ctx 线性分量、第 3 字节含签名计数器（奇偶交替 27/f3）
- **X-Khronos**: metasec 内部缓存时钟（RPC 空闲期间按批推进, 跨秒正常）
- **策略判定**: VMP 核心（274C60+2810d4）+ 轮换密钥 → 纯算死路；交付形态 = 在线 oracle（App+frida RPC 即签名服务）
- 反检测: 勿 hook 275064 区（checksum 反 hook）；264E3C 加密函数指针 0xF5D56A94/0x9EBB/0xFF5F XOR 解指针

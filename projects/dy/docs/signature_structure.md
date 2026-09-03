# 八神签名结构还原 — 抖音 38.0.0 / libmetasec_ml.so

> 2026-08-24 定稿。方法：静态（IDA 9.2 反汇编 dec3/dec4）+ 动态（hook20 三层观测 + RPC oracle 112 组差分分析 + SF-012 字节级验证）。
> 采集数据：`../capture/oracle_dataset.json`（112 组）、`../capture/dy_hook20.log`（真实请求 3 次全量）

## 0. 总览：签名入口与调用链

```
libsscronet.so 411e74 (OnBeforeURLRequest)
  → BL 3411b4 → BLR [[[X19+8]+0x40]+0x28]+0x18 = sub_47A31C
    → libmetasec_ml.so+0x28065c  回调: char*(char* url, char* headers) → char*
      → 264E3C(out, mode, msg) ×2  (mode=1 内部日志签名 / mode=2 八神签名)
        → 274C60 VMP 解释器（syscall 包装 + 0x312768B checksum 反 hook + 环境检测）
      → 输出 "name\r\nvalue\r\n..." 串，由 sub_2ED608(mode=2) 解析 → sub_37ED64 SetHeader
```

- 264E3C = 签名主函数（init-once 0x3E31C4 + 加密函数指针 0xF5D56A94/0x9EBB/0xFF5F XOR 解指针 BLR + 事件注册循环）
- 274C60 = 系统层（⚠️ 勿 hook 275064 区 syscall 包装，有 11-dword 滚动 checksum 0x312768B 反 hook）
- 2810d4 = VMP dispatcher（状态魔数 0xC19E4AE5 → handler 表）
- 282020 = URL query 提取（strchr '?'/'#'）—— 决定 Gorgon 输入范围
- 168820 = XOR 字符串解密器（a^b→c）；MS SDK (mssdk.bytedance.com) 遥测串在 0x3E5F80 区

## 1. 输出格式

28065c 返回 `name\r\nvalue\r\n...` 拼接串（name 含 `X-` 前缀），按出现顺序：

```
X-Argus\r\n<8B base64>\r\nX-Gorgon\r\n<52 hex>\r\nX-Helios\r\n<48B base64>\r\n
X-Khronos\r\n<10-digit ts>\r\nX-Ladon\r\n<8B base64>\r\nX-Medusa\r\n<~1220B base64>
```

分支：URL 无 query / 过短 → 仅输出 `X-Neptune\r\n-8|50:51:59:30:40:47:49:39`（最小签名/错误响应）。

## 2. 各头结构（差分结论）

### X-Argus — ✅ 完全破解（SF-012 字节级验证 12/12 + 历史 8/8）

```
X-Argus = base64( LE32( unix_ts ) )    # 4 字节小端时间戳
验证: ts=1787565621 → NRaMag==  (0x6A8C13E5 → e5 13 8c 6a)  全 12 点跨秒吻合
真实请求: ts=1787564379 → WxGMag== / 4464 → sBGMag== / 4546 → AhKMag==
不依赖 url/headers；RPC 下 ts 与 X-Khronos 同源（App 内部缓存时钟，批量调用期间每批推进）
```

### X-Khronos — ✅ 同源时钟

```
十进制 unix 时间戳 = X-Argus 所用的同一 ts。
注意: metasec 内部时钟由 App 网络活动驱动刷新；纯 RPC 空闲调用期间跨秒会正常推进（12 点验证），
      但长时间无 App 活动时可能滞后（hook20 观测：真实请求精确，RPC 批次内恒定）。
```

### X-Gorgon — 结构破解（keyed hash，离线不可复现）

```
26 字节 = 52 hex:
  [0:2]  84 04            固定版本
  [2:4]  ctx-flag         2B，随上下文轮换（高位偶数化: 0x40/0x80/0x20/0x60/0xe0/0xa0 组合）
  [4:6]  00 01            固定
  [6:24] hash 18B = [4B keyed-hash(query)] + [1B ctx] + [13B ctx-token]

输入范围（6 变体实测）:
  参与:  query 字符串（键与值都算，单字符变化 → 4B 全变）
  不参与: path 尾段、scheme(https→http)、fragment、headers（G3 20 变体 → hash 恒定）
  与静态 282020 strchr('?'/'#') 提取器完全一致

keyed hash: 4B ≠ md5/sha256/crc32/adler32(query) → 含上下文密钥（HMAC-XXX[:4] 级）
上下文轮换: ~0.5-0.6s（App 后台网络活动驱动），轮换时 hash 18B 全变；
             同上下文内 4B 对 query 敏感、14B 恒定
```

### X-Medusa — 头部破解

```
base64 解码 ~914B:
  [0:4]    LE32(内部 ts)   （G1: cd138c6a ↔ ts+5；真实: 5e118c6a ↔ ts+3）
  [4:end]  ~910B 加密 payload（尾部 16B 疑似 AES-GCM tag: 7a7806c09435d711fff8d711fef8e50c）
  时间敏感（同输入每次不同）；结构暗示 AES-GCM（nonce+ct+tag）或固定密钥流 XOR + HMAC
```

### X-Ladon — 部分破解

```
4B base64。组内第 4 字节恒定、跨组随上下文线性变化（G1 0x71 → G6 0x41）；
G6 组内第 3 字节 27/f3 按调用奇偶交替（含签名计数器）。
第 4 字节 = f(ctx)，前 3 字节对 headers 子集敏感（20 变体 → 仅 3-5 个值，被规范化/过滤）。
```

### X-Helios — 结构已知

```
36B raw（48 字符 base64）。对 url/headers/时间全敏感（差分: 全部变化）。
首 4B 无时间戳特征（d65af939），算法在 VMP 内部。
```

### X-Neptune（第 9 头，新发现）

```
URL 无 query 时单独输出: -8|50:51:59:30:40:47:49:39  （-8 疑为错误码/最小签名）
真实请求未观测到（合法 URL 走 6 头路径）。
```

## 3. 算法类别判定与策略

| 判定 | 结论 |
|------|------|
| 核心计算 | VMP（274C60 解释器 + 2810d4 dispatcher）+ 加密函数指针 + ~0.5s 轮换密钥 |
| 离线纯算 | **不可行**（VMP 字节码 + 轮换密钥；Gorgon 4B/Ladon/Helios 均为 keyed hash） |
| 可用策略 | **在线 oracle**：App 运行 + `hooks/dy_hook21.js` RPC → `oracle(url, headers)` / `oraclebatch()` |
| 已破解可离线 | X-Argus（= LE32(ts)）、X-Khronos（= ts）、Medusa 头 4B、Gorgon 骨架 |

## 4. 采集与验证资产

| 文件 | 内容 |
|------|------|
| `../capture/oracle_dataset.json` | 112 组输入输出对（G1 重复/G2 url 变/G3 hdr 变/G4 随机/G5 边界/G6 真实 cookie 变体） |
| `../hooks/dy_hook21.js` | 纯 RPC oracle（无 Interceptor 噪音） |
| `../scripts/dy_oracle_collect.py` | 分组批量采集器（adb pidof 直连，绕过 App 反枚举） |
| `../capture/dy_hook20.log` | 真实请求 3 次全量 + 264E3C/274C60 内层观测 |

## 5. 反检测要点（复现必读）

1. App 运行一段时间后从 frida 进程表**反枚举消失** → `adb shell pidof` 拿 pid 直连 `attach(pid)`
2. frida 16.5.7 RPC 方法名**必须全小写**（Python 绑定会 lower() 查找）
3. 勿 hook 274C60 内部 275064 区（checksum 反 hook）；hook 函数入口安全
4. RPC 调用在 frida 线程执行，28065c 内部有 TLS/全局状态——空 url 返回 NULL（App 不崩）
5. App 重启后 libmetasec_ml.so 基址变化（ASLR）→ 脚本动态 Process.findModuleByName

# 抖音 Cronet TLS 指纹 — 抓取与伪造评估

> 2026-08-28 采集。目标：伪造 libsscronet 网络层指纹绕过 hit_shark。
> 脚本：`scripts/parse_clienthello.py`；抓包：`capture/dy_tls.pcap`、`dy_tls2.pcap`。

## 1. 采集方法

```
真机 tcpdump -i any -s 0 -w ... port 443（root）
+ force-stop → monkey 冷启动 → deep link snssdk1128://search?keyword=xxx 触发
+ 拉 pcap 到 PC，纯 Python 解析 ClientHello（SLL linktype=113 + TLS 1.2/1.3）
```

## 2. 核心发现：JA3 的「随机性」来自 GREASE，去 GREASE 后指纹稳定

抖音 Cronet（libsscronet + libttboringssl）使用 **BoringSSL GREASE 机制**，
在 cipher 首位、curve 首位随机插入 GREASE 值（0x0A0A/0xFAFA/0x2A2A/0xAAAA…），
导致原始 JA3 每次握手都变。**过滤 GREASE 后，指纹两次抓包完全一致**：

| 连接类型 | 稳定 JA3（去 GREASE） | ciphers | ext | ALPN |
|---------|----------------------|---------|-----|------|
| 字节 Cronet HTTP/2（zijieapi.com，搜索/API 类同栈） | `cd08e31494f9531f560d64c695473da9` | 15 | 16 | h2 + http/1.1 |
| 视频 CDN（douyinvod.com） | `c9e756f0d1d7f395f835b0b3d734b98c` | 18 | 11 | — |

## 3. 稳定指纹完整参数（伪造目标 = 搜索/API 类）

```
version:     771 (0x0303 TLS 1.2)
ciphers(15): 4865,4866,4867,49195,49199,49196,49200,52393,52392,49171,49172,156,157,47,53
             (TLS1.3 三件套 + ECDHE 套件 + CHACHA20 + 传统套件)
extensions(16): 0,23,65281,10,11,35,16,5,13,18,51,45,43,27,17513,21
             (SNI,EMS,reneg,supported_groups,ecpf,session_ticket,ALPN,OCSP,
              sig_algs,SCT,key_share,psk_modes,supported_versions,compress_cert,
              17513=ALPS,padding)
curves(3):   29,23,24  (x25519, secp256r1, secp384r1)
point_fmt:   0
GREASE:      cipher 首位随机 + curve 首位随机（BoringSSL 反指纹）
```

## 4. 私有扩展 0x4469 = ALPS

extension `17513`(0x4469) 内容 `0003026832` = **ALPS（Application-Layer Protocol Settings）**，
声明 ALPN 协议 `h2`（长度 2 + "h2"）。这是 Chromium 标准行为（HTTP/2 over TLS 的 ALPS），
**非字节私有、可伪造**（Go utls 支持 ALPS）。

## 5. 伪造评估

| 项 | 状态 |
|----|------|
| 稳定指纹已提取 | ✅ JA3=cd08e314…（去 GREASE） |
| 关键扩展识别 | ✅ 0x4469 = ALPS("h2")，非私有 |
| 伪造工具 | ⚠️ 需 Go utls（本机无 Go）；tls-client/curl_cffi 预设指纹不含此字节 Cronet JA3 |
| HTTP/2 帧层 | ⚠️ SETTINGS/流优先级细节未采集，可能还有一墙 |
| 搜索域名精确握手 | ⚠️ 两次 tcpdump 均未抓到 search5-*.amemv.com（连接预热复用 / 或需更早触发） |

## 6. 关键局限（伪造成功≠搜索接口 PC 复刻）

即使 TLS+HTTP/2 指纹 100% 伪造成功，搜索接口**仍有八神签名墙**：
`libmetasec_ml.so` VMP + ~0.5s 轮换密钥 → 离线不可算（见 `signature_structure.md`），
签名仍依赖真机 oracle（`hooks/dy_hook21.js`）。故「PC 独立复刻」= 指纹墙 + 签名墙，
单拆指纹墙不足以脱离真机。

## 7. 伪造实测（2026-08-28，tlsforge 工具）

工具：`projects/dy/tlsforge/`（Go 1.22.5 + refraction-networking/utls v1.6.7），
`tlsforge.exe -url ... -body ... -header ... [-h2]`。
TLS 指纹精确对齐 §3（cipher 16 含 GREASE / extension 16 含 ALPS / curve 4 含 GREASE）。

| 传输 | 结果 |
|------|------|
| HTTP/1.1（ALPN http/1.1） | ❌ `antispam_check/hit_shark`（响应 brotli 压缩，business_data 空） |
| HTTP/2（ALPN h2 + x/net/http2） | ❌ `antispam_check/hit_shark`（同上） |

→ **结论**：JA3 精确对齐 + HTTP 版本对齐，**仍 hit_shark**。判定维度在更深层，
未对齐项（按嫌疑）：
1. **HTTP/2 帧细节**：Go x/net/http2 的 SETTINGS 帧 / 流优先级 / WINDOW_UPDATE 与
   Chromium Cronet 不同（这是最大嫌疑）
2. **signature_algorithms 具体值**：tlsforge 用 utls 默认 Chrome 值，未对齐字节真实值
3. **JA4 指纹**（含 SNI/ALPN/version/cipher数/ext数的二级 hash）
4. **QUIC**：若搜索域名走 HTTP/3，则 TCP+TLS 伪造方向整体错位

工程判断：hit_shark 是 Cronet 网络栈的多层指纹，非单一 JA3；逐层深挖（HTTP/2 帧 +
sig_algs + JA4 + QUIC）工作量深不见底、每层可能仍有下一层，与 `search_api.md`
「PC 独立复刻不可行」结论一致。搜索数据走方向 C（App 代发）仍是唯一稳定路径。


# 协议直发验证报告（2026-09-10）

## 结论摘要

**协议层签名头已完整获取，且经直发验证有效** —— 服务端从 `-99999`（风控拒绝）变为返回加密 chunk 流。

## 一、技术链路（全部打通）

```
hook libsscronet.so!SSL_write
  → HTTP/2 帧解析（HEADERS type=0x01，处理 PADDED/PRIORITY flag）
  → HPACK 索引解码（RFC 7541 §5.1 整数 + 静态表 61 项 + 动态表）
  → HPACK Huffman 解码（RFC 7541 附录 B 完整 256 项表）
  → 完整请求头明文
```

**验证方式**：解出的 `:method`/`:authority`/`:path`/`cookie` 与业务逻辑一致，且能还原 22 条 Cookie。

## 二、★ 重大修正：八神签名头真实存在

**推翻此前结论**（"八神不在搜索/评论链路"）。此前依据是 Java 层 `MSManager.frameSign` hook 0 次命中；
**实际八神头在 native 层直接注入 TLS 流**，Java 层完全不可见。

实测抓到的完整签名头：

| 头 | 说明 |
|---|---|
| `x-tt-token` | `0051e8bf...3.0.4` 长期令牌（跨请求一致） |
| `bd-ticket-guard-key-sign` | 128 hex |
| `x-tt-token-supplement` | 补充令牌 |
| **`x-argus`** | **八神 Argus** |
| **`x-gorgon`** | **八神 Gorgon** |
| **`x-ladon`** | **八神 Ladon** |
| **`x-khronos` / `x-helios` / `x-medusa`** | 字节风控族 |
| **`x-ss-stub`** | 请求体签名 |
| `x-ss-dp` / `x-tt-dt` | 设备/DP 令牌 |
| `x-vc-bdturing-sdk-version` | 4.1.1.cn（验证码 SDK） |

**Cookie 链（22 项）**：`sessionid` / `sid_guard` / `odin_tt` / `d_ticket` / `multi_sids` /
`install_id` / `passport_mfa_token` / `passport_assist_user` / `session_tlb_tag` …

## 三、直发验证结果

**实验设计**：用抓到的**真实 header + Cookie + URL + body** 直发评论请求
（仅将 host 保持原值，body 与 URL 逐字复用）

| 指标 | 结果 |
|---|---|
| HTTP 状态 | 200 |
| **风控码 `-99999`** | ✅ **消失**（此前无签名头时必现） |
| 响应体 | **69 字节加密二进制 chunk**（`ChunkDataStream` 应用层加密） |
| 压缩格式探测 | gzip/zlib/brotli/zstd **均不是** |
| ASCII 可读率 | 0.49（密文） |

**判定**：**签名层已通过**（服务端接受请求），**剩余障碍是响应体的应用层解密**。

## 四、待解（明确的下一步）

| 项 | 状态 |
|---|---|
| 请求签名（发送方向） | ✅ 已解决（复用抓取的头即可） |
| 响应体加密（接收方向） | ❌ **未解**：69 字节密文，需逆 `ChunkDataStream` 的解密逻辑 |
| 评论接口走 QUIC | ⚠️ 实证：点击评论后 `SSL_write` 零新增帧 → 该接口走 QUIC(UDP)，故评论帧抓不到 |

**响应解密路径**：
1. `ChunkDataStream` 的解密实现在 `com.bytedance.android.chunkstreamprediction` 包
2. 或 hook `ChunkDataStream` 的 chunk 解密函数（在收到密文后、`onNext` 前）

## 五、交付物

| 文件 | 内容 |
|---|---|
| `hooks/cap_h2_headers.js` | SSL_write hook（只回传 HEADERS 帧） |
| `scripts/cap_h2_headers.py` | HTTP/2 + HPACK + Huffman 完整解码器 |
| `capture/signature_headers.json` | **完整签名头 + Cookie（可直接复用）** |
| `scripts/direct_comment_test.py` | 协议直发验证脚本 |
| `capture/direct_comment_response.txt` | 直发响应（加密 chunk） |

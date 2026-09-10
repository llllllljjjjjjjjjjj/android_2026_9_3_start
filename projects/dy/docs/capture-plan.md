# dy 抓包配置（eCapture 失败后的改库 r0capture 方案）

## 环境就绪状态（2026-09-07）
- 设备: Pixel 4 `9C181EC3BF7E0D`，Android 10（**内核 4.14.170**，<5.5 → eCapture/eBPF 不可用）
- frida-server: `/data/local/tmp/florida-server`（16.5.9）已运行 + `adb forward tcp:27042 tcp:27042` ✅
- frida 客户端: `.venv-frida-16.5.7`（16.5.7）验证 `frida-ps -H 127.0.0.1:27042` 可列进程 ✅
- 抖音: com.ss.android.ugc.aweme 38.0.0，userId/uid=10213

## 方案定论（真实判官：so 符号已字节级验证）
- 抖音 TLS = `libttboringssl.so`（367KB，导出 `SSL_read`@0x4894c、`SSL_write`@0x48bb0、`SSL_do_handshake`、`SSL_new/connect/free`）
- `libsscronet.so` 对 SSL_read/SSL_write 为 **UND（导入）** → 实际实现收敛于 libttboringssl
- 结论: hook `libttboringssl.so` 的 SSL_read/SSL_write 即可覆盖 cronet/TTNet 的 **TCP-TLS 明文**
- r0capture 原版在 Android 硬编码 hook `*libssl*`（系统 conscrypt），抓不到抖音；已定制（见下）

## 已落盘工具
| 文件 | 作用 |
|---|---|
| `projects/dy/hooks/script.js` | 定制 Frida 脚本：hook `libttboringssl` 的 SSL_read/SSL_write，明文 send 回 Python |
| `projects/dy/hooks/run_capture.py` | runner：attach/spawn 抖音，明文写 `dy_tls_plain.txt`，关键头(token/argus/install_id)实时标注 |
| `projects/dy/so_analysis/libttboringssl.so` 等 4 个 so | 符号验证与后续 IDA/native 分析用 |

## 执行命令
```powershell
cd projects\dy\hooks
& ..\..\..\.venv-frida-16.5.7\Scripts\python.exe run_capture.py -f -o ..\capture\dy_tls_plain.txt
# attach 已运行进程: run_capture.py -p <pid> -o ..\capture\dy_tls_plain.txt
```

## 关键风险 / 止损线
1. **QUIC(UDP) 抓不到**：SSL_read/SSL_write 只覆盖 TCP-TLS；抖音大量走 cronet QUIC(UDP/443)。
   若文本落盘为空或仅少量头 → 说明核心流量走 QUIC，需二选一：
   - `iptables -I OUTPUT -m owner --uid-owner 10213 -p udp -j DROP` 逼 QUIC 降级 TCP（记录恢复 `-D` 同规则）
   - 或转 `android-dynamic` 抓 cronet 层 QUIC 明文（native SO 分析，recon 不越界）
2. **反调试/Frida 检测**：抖音有反 Frida 风险；spawn 失败/秒退 → 转 android-dynamic 按反检测流程走，不在 recon 死磕
3. **恢复清单**（抓完必须）: 删 DROP-UDP 规则 / `android_proxy_clear` / 移除 `adb forward --remove tcp:27042` / force-stop 抖音恢复前台
4. **同接口同错误连续 3 次停止**（验收纪律）

## 输出目录
`projects/dy/capture/`（dy_tls_plain.txt 及后续抓包取证）

## 抓包成果（2026-09-07 已实证）
- 捕获 **16.5MB TLS 明文**（`capture/dy_tls_plain.txt`），抖音 38.0.0 进程存活、无反 Frida 秒退
- 关键实样（`capture/headers_sample.txt`）:
  - `X-Tt-Token` = ClientKey（128+ hex，尾缀 `3.0.4` = kms_version）→ 静态结论被动态证实
  - `bd-ticket-guard-key-sign`（64 hex，TicketGuard 风控签名）
  - `x-tt-token-supplement` / `x-bd-kmsv` / `x-tt-passport-mfa-token` / `x-vc-bdturing-sdk-version`（bdturing 风控）
  - `x-tt-ext-info`（`version=4.2.243.28-douyin`）、`x-tt-abtest`
- 明文来源 = **HTTP/1.1 WebSocket 长连接升级请求**（frontier-aweme-*.amemv.com），187 处文本头
- 局限: 普通 API 走 HTTP/2，头被 HPACK 压缩二进制不可直接读；需 HPACK 解压或上层 Java Hook（转 android-dynamic）
- 设备已恢复基线（forward 清空/抖音停/http_proxy null）

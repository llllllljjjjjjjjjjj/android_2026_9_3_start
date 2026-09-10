# SSL Pinning 绕过（8 方案详细手册）

> 本文件由 `SKILL.md §4 SSL Pinning 8 方案选择器` 引用，属于**按需加载**层：按 pinning 强度/栈类型选绕过方案、对比各方案 CA/Root/Flutter/A14 支持、ecapture 命令时读。

---

# §4 SSL Pinning 8 方案选择器

```
SSL Pinning 强度
├─ 弱/无 → Reqable + TrustMeAlready
├─ 中(标准 OkHttp/TrustManager) → objection sslpinning disable / JustTrustMe(LSPosed)
├─ 强(XHS级，系统代理绕行) → mitmproxy 透明 + iptables REDIRECT
├─ Flutter(BoringSSL in libflutter) → Frida hook ssl_session_verify_cert_chain / frida4burp / 内存patch
├─ 自研 TLS(libtnet/静态 BoringSSL) → ecapture(eBPF, 无需CA, 内核抓明文) / IDA 定位 SSL_read/write + Native Hook
├─ ANet/QUIC(阿里系) → Hook libxquic xqc_h3_request_send_headers/send_body（见 android-recon §3.4）
└─ Android14+ /apex 只读证书 → MoveCertificate + OverlayFS / Magisk 注入
├─ 抖音 TTNet → eCapture text --hex 零注入（pcap 模式因魔改 boringssl 偏移常 auth-tag mismatch）
└─ Android14+ /apex 只读证书 → MoveCertificate + OverlayFS / Magisk 注入（真路径 `/apex/com.android.conscrypt/cacerts/`）
```

| 方案 | CA | Root | Flutter | A14+ | 复杂度 |
|------|:--:|:----:|:-------:|:----:|:------:|
| Reqable+TM | ✅ | ❌ | ❌ | ⚠️ | 🟢 |
| objection | ✅ | ✅ | ❌ | ✅ | 🟢 |
| mitmproxy 透明 | ✅ | ✅ | ✅ | ✅ | 🟡 |
| frida4burp | ✅ | ✅ | ✅ | ✅ | 🟢 |
| Frida native hook | ✅ | ✅ | ✅ | ✅ | 🟡 |
| **ecapture(eBPF)** | **❌** | ✅ | ✅ | ✅ | 🔴 |
| Patched APK | ✅ | ❌ | ✅ | ✅ | 🟢 |

```bash
# ecapture：内核层抓 TLS 明文，不需 CA（Android10+/Kernel5.5+）；绕代理检测（ct_client 配证书没网的正解）
adb shell su -c "/data/local/tmp/ecapture tls -m text -p <PID>"
```

# amemv.com 证书校验绕过全记录（抖音 38.0.0）

> 目标：Charles 抓取 amemv 明文流量，查看 x-argus/x-gorgon 签名头。
> 结论：**字节魔改 BoringSSL 的 custom_verify 回调语义反转——返回 0=通过、1=拒绝**。把回调返回值 1 改成 0 即绕过。
> 状态：✅ 已验证生效（v10 探针，amemv 明文可见）。
> 合规：仅授权安全研究 / 自有设备调试 / 教育用途。

---

## 1. 最终绕过方案（一句话）

frida hook 抖音的 `custom_verify` 回调（libsscronet.so+0x3dbb44），对 API 主机（amemv 等）的返回值 **1（拒绝）强制改为 0（通过）**，并清零 alert 参数；同时保留 QUIC 降级（视频流必须走 TCP）。

最终脚本：[hooks/dy_hook30_probe.js](../hooks/dy_hook30_probe.js)

---

## 2. 环境链路（先决条件）

```
手机 Kitsunebi(全局VPN, SS AES-128-GCM, 服务器127.0.0.1:8388)
  → adb reverse tcp:8388 tcp:8388（桥）
  → PC Xray（SS入站8388 + sniffing destOverride http/tls → SOCKS 8889）
  → Charles（HTTP代理8888 + SSL Proxying）
```

- 真机：Pixel 4 (flame)，serial `9C181EC3BF7E0D`，APatch root
- frida：设备 `/data/local/tmp/florida-server`（魔改免杀，16.5.9 自报 16.5.10-dev.0）或 `/data/local/tmp/f1657`（官方 16.5.7 回退）；PC 客户端统一 `.venv-frida-16.5.7`（16.5.x）
- Charles 根证书已入系统库（d18fce22.0，重启不丢）
- QUIC 必须降级：视频流默认走 UDP，而 adb reverse 只转 TCP → 不降级视频必挂

---

## 3. 试错时间线（v4 → v10）

| 版本 | 做了什么 | 结果/发现 |
|------|---------|----------|
| v4 | 按 2 参数读 `SSL_CTX_set_custom_verify`，包装 cb=0x1 | **崩溃**（access violation accessing 0x1）。字节版是 3 参数 (ctx, mode, cb)，0x1 是 mode=SSL_VERIFY_PEER |
| v5 | 修正为 args[2]；包装 libvcn.so 视频回调 | 视频异常。后确认主因是 amemv TLS 全挂导致 feed 拉不到；但从此**跳过 libvcn.so**（视频路径不碰） |
| v6 | NativeFunction 直调 ERR_peek_error/ERR_error_string_n | 直调失败 "(err read fail)" → 教训：**魔改库内部函数优先用 Interceptor hook，别直调** |
| v7 | hook ERR_peek_error（按 returnAddress 过滤来自 SSL_get_error 内部的调用） | 抓到队列顶 raw=0x230000ca = lib=35 reason=202；sub_3DB8EC 映射 → net_error=-202 ERR_CERT_AUTHORITY_INVALID |
| v8 | hook ERR_put_error 抓回溯 | **lib35/202 是 sscronet 自己在 0x3dbffc 合成的记号错误**（file=(null):-1）；X509_verify_cert 全程未被调用 → 排除第二道 X509 校验 |
| v9 | AUTOCLEAR：回调放行后立即 ERR_clear_error() | **失败**。清得太早：真错误 lib16/125 是回调返回**之后**才被塞入的（BT: libttboringssl+0x38e84） |
| IDA | 反汇编 sub_38D0C（证书校验函数） | **语义反转发现**（见 §4） |
| v10 | FORGE 反转：API 主机回调返回 1 → 改 0 + alert 清零 | ✅ **成功**。amemv 握手通过（ssl_error=0），Charles 明文可见 |

---

## 4. 关键发现

### 4.1 回调返回值语义反转（核心）

IDA 反汇编 `sub_38D0C`（libttboringssl.so+0x38d0c，魔改版证书校验）逻辑：

```
custom_verify 回调返回 0 → 清内部标记 → 正常通过（返回 0）
custom_verify 回调返回 1 → 检查 config+0xE8（验证模式字节）：
    位=0 → ERR_clear_error() → 通过
    位≠0 → 塞 ERR_put_error(16, 125, handshake.cc:393) → 握手死
```

标准 BoringSSL 约定"1=放行"，**字节魔改版反转为 0=通过、1=拒绝**。sscronet 的回调对 Charles 证书返回 1（拒绝）——之前一直误读为放行，v9 的 forge（0→1）方向完全相反。

**对照实验早就给出答案**：`ib.snssdk.com ret=0` 后握手成功，当时被误读为"拒绝后靠会话恢复重连"，实为"0=通过"。

### 4.2 记号错误（lib35/202）不是根因

`ERR_put_error(35, 202, file=(null):-1)` 是 sscronet 在 libsscronet+0x3dbffc 运行时合成的记号（file=(null):-1 是合成特征），用于它自己的错误上报。清它没用，真正的杀手是回调拒绝后 BoringSSL 自己塞的 lib16/125。

### 4.3 错误码速查

- `ssl_error=0`（SSL_ERROR_NONE）+ do_hs_ret 正数 → 握手成功
- `ssl_error=1`（SSL_ERROR_SSL）→ ERR 队列有真错误 → 握手失败
- `ssl_error=2`（WANT_READ）→ 正常等待数据（隧道通的表现）
- `ssl_error=5`（SYSCALL）→ 系统层错误，零星出现可忽略

---

## 5. 关键偏移表（抖音 38.0.0，按 IDA 基址）

### libttboringssl.so
| 符号/用途 | 偏移 |
|----------|------|
| SSL_do_handshake | 0x486c0 |
| SSL_get_error | 0x4901c（0x4901c-0x49134） |
| SSL_get_servername | 0x49d6c |
| SSL_CTX_set_custom_verify | 0x49dac |
| SSL_set_custom_verify | 0x49db8 |
| SSL_get_SSL_CTX | 0x4a638 |
| SSL_CTX_set_verify | 0x50810 |
| SSL_get_verify_result | 0x50834 |
| sub_38D0C（证书校验，魔改 ssl_verify_peer_cert） | 0x38d0c |

### libttcrypto.so
| 符号 | 偏移 |
|------|------|
| ERR_peek_error | 0xb5f8c |
| ERR_clear_error | 0xb6014 |
| ERR_put_error | 0xb6594 |
| X509_verify_cert | 0xdab60 |
| X509_STORE_CTX_get_error | 0xdbe78 |

### libsscronet.so
| 用途 | 偏移 |
|------|------|
| 握手循环 | 0x3DA454 |
| ssl→net_error 映射 | 0x3DB8EC |
| 合成记号错误调用点 | 0x3dbffc |
| custom_verify 回调 | 0x3dbb44 |

### 结构偏移
| 结构 | 字段 |
|------|------|
| ssl + 0x8 | config 指针 |
| config + 0x30 | custom_cb |
| config + 0xE8 | 验证模式字节（非零=严格模式） |
| SSL_CTX + 0xC8 | custom_cb |
| SSL_CTX + 0x130 | mode |

---

## 6. 复现步骤（手机重启后完整流程）

```powershell
# 1. 确认设备（serial 9C181EC3BF7E0D）
adb devices

# 2. 重启 frida server（重启后进程没了）
adb shell su -c "nohup /data/local/tmp/florida-server >/dev/null 2>&1 &"
adb shell su -c "ps -A | grep florida"

# 3. 重建两条隧道（重启后失效）
adb reverse tcp:8388 tcp:8388
adb forward tcp:27042 tcp:27042
adb reverse --list ; adb forward --list

# 4. 启动 Xray（窗口保持开着）
D:\Xray-windows-64\xray.exe run -c D:\reserve_agent\skills-portable-test\projects\dy\scripts\xray_ss2charles.json

# 5. Charles：HTTP Proxy 8888 + SSL Proxying 开启；手机 Kitsunebi 连接 127.0.0.1:8388

# 6. 注入 v10 探针（注意 PowerShell 需要 & 调用符）
& "D:\reserve_agent\skills-portable-test\.venv-frida-16.5.7\Scripts\frida.exe" -H 127.0.0.1:27042 -f com.ss.android.ugc.aweme -l D:\reserve_agent\skills-portable-test\projects\dy\hooks\dy_hook30_probe.js

# 7. 刷评论区 → Charles 里找 /aweme/v1/comment/ 请求 → Contents → Request Headers → x-argus / x-gorgon
```

RPC 开关（注入后用 `%resume` 或 frida 交互）：
- `forge(v)`：回调拒绝(1)→通过(0) 的开关
- `autoclear(v)`：回调后清 ERR 队列（双保险，保留）
- `status()`：统计

---

## 7. 教训清单

1. **魔改库的 API 语义不可信**——参数个数（v4）、回调返回值含义（v9→v10 反转）都要从反汇编验证，不能照搬上游 BoringSSL 的约定。
2. **frida 回溯帧是返回地址**：BT 第一帧 = 调用者内部（如 +0x38e84 是 `LDRB` 而非 `BL`）。
3. **NativeFunction 直调魔改库内部函数易崩**（v6），优先 Interceptor hook。
4. **包装回调有副作用**：先跳过无关模块（libvcn.so），能排除变量。
5. **"清错误"要看塞入时序**（v9 失败）：观测 ERR_put_error 的 BT + 回调日志的相对顺序，别想当然。
6. **file=(null):-1 的错误是运行时合成的记号**，不是真实源码位置，别去源码里找。
7. **多 host 平行对照**：ib.snssdk.com `ret=0`+`[hs] OK` 与 amemv `ret=1`+FAIL 的对比，答案早已在日志里——先怀疑自己读反了语义。
8. **Windows PowerShell**：带引号路径的程序要用 `&` 调用运算符。
9. **手机重启后** reverse/forward/frida-server 全部失效，必须重建；系统证书不丢。
10. 若视频刷不动：先查 QUIC 降级是否生效（UDP 过不了 adb reverse 的 TCP 桥）。

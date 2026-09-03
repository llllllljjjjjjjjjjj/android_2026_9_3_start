# 携程 `x-payload-source` 签名逆向

> 目标：还原 `x-payload-source` 请求头签名（HTTP 请求头，每个 SOA2 请求必带）
> 结论：**设备绑定 + 会话绑定的 native 签名，纯离线不可行 → 策略 E（Frida RPC 在线签名）**

---

## 1. 结论摘要

| 项 | 值 |
|----|-----|
| 签名头 | `x-payload-source`（75 hex） |
| 签名输入 | `md5(body).toLowerCase()` 的 32 字节 ASCII |
| native 库 | `libscmain.so`（`System.loadLibrary("scmain")`） |
| JNI 方法 | `SecurityUtil.simpleSign(byte[], String)`（RegisterNatives 动态注册） |
| 密钥 | Android Keystore（`secp256r1` ECDSA + `DIGEST_SHA256`）+ 设备指纹 |
| 输出结构 | `[32 hex 设备恒定] + [11 hex 会话变化] + [32 hex 输入相关]` |
| 可离线还原 | ❌ 否（设备密钥在硬件/TEE，会话态每次启动变化） |
| 推荐策略 | **E：Frida RPC 在线签名**（已验证可用） |

---

## 2. 完整调用链

```
CTHTTPClient.generateRequestDetail()                          // ctrip/android/httpv2/CTHTTPClient.java:882
  └─ map.put("x-payload-source",
        C22725a.m66709k(md5(body).toLowerCase()))             // hj0.C22725a = "BaseSign"
            └─ f68038d.mo54118e(str.getBytes(), "getdata")    // 接口 hj0.C22725a$a
                └─ C19294a$p.mo54118e()                        // ctrip/base/init/C19294a.java:1163
                    └─ SecurityUtil.getInstance().bnSimpleSign(bytes, "getdata")
                        └─ native simpleSign(byte[], String)   // libscmain.so
```

关键类：
- `hj0/C22725a.java`（BaseSign 委托，`m66709k` = simpleSign 入口）
- `ctrip/base/init/C19294a.java`（内部类 `p implements C22725a.a`，注册 `m66707i(new p())`）
- `ctrip/android/security/SecurityUtil.java`（native 方法声明 + `System.loadLibrary("scmain")`）

签名相关 native 方法（SecurityUtil）：
| 方法 | 用途 |
|------|------|
| `simpleSign(byte[], String)` | **x-payload-source**（输入 md5(body)，操作 "getdata"） |
| `strongSign(byte[], String)` | 强签名 |
| `getToken()` / `getToken2()` / `getLabel2()` | x-payload-bnlabel / bnlabel2 等 token |
| `appBootTime()` | 启动时间 |
| `init(Context, int)` | 初始化（收集设备指纹 + 初始化密钥） |

---

## 3. 输出结构（75 hex 三段式，实测）

```
x-payload-source = C85B162EB3128973D7039908AE2D6AE9 | 5EF3926A14E | 86A77A9E2B48E59D168B0CB3783C4121
                   ├──────── 32 hex 设备恒定 ────────┤ ├─ 11 hex ─┤ ├── 32 hex 输入相关 ──┤
```

| 段 | 长度 | 行为 | 推断 |
|----|------|------|------|
| Part1 | 32 hex (16B) | 跨会话恒定 | 设备密钥指纹（Android Keystore 派生），跨设备会变 |
| Part2 | 11 hex | 每次 App 启动变化 | 会话级随机值/时间戳片段（会话态） |
| Part3 | 32 hex (16B) | 随 md5(body) 变化 | 对 `md5(body)` + 密钥 + 会话 的 keyed 运算 |

实测三个会话的 Part1 完全一致 `C85B162EB3128973D7039908AE2D6AE9`；
Part2 分别为 `E0C2916A14E` / `50F1926A14E` / `5EF3926A14E`（每次启动变化，尾 6 hex `6A14E` 恒定）。

Part3 已排除：`md5(in)`、`md5(in_hex)`、`sha1(in)[:32]`、`md5(part1||in)`、`hmac-md5(part1, in)` 等
简单哈希假设——是密钥参与的非标准运算（密钥在 native 层）。

---

## 4. `libscmain.so` 静态线索

`libscmain.so`（3.0MB，arm64-v8a）字符串分析：

- **Android Keystore 硬件密钥**：`AndroidKeyStore` / `KeyGenParameterSpec` / `KeyPairGenerator` /
  `generateKeyPair` / `KeyStore` / `Certificate` / `ECGenParameterSpec` / `secp256r1` / `DIGEST_SHA256`
  → 签名密钥是 **ECDSA P-256 硬件密钥**（TEE/StrongBox 内，不可提取）
- **设备指纹采集**：`getActiveCpuCount` / `getFreeDiskSpace` / `getUseDiskSpace` / `getBatteryStatus` /
  `getScreenBrightness` / `getTotalDiskSpace` / `getLocaleIdentifier` / `getAppNativeDir` / `getActiveMemory` /
  `getInActiveMemory` / `getAppBootTime`
- **环境/多开检测**：`com.yooha.antisdk.MainActivity` / `com.shaker.wxxh.moli.fs` / `com.trigtech.privateme` /
  `godinsec_private_space` / `multiaccount` / `ldAppStore` / `/system/priv-app/`
- **C++ 实现**：libc++ `std::__ndk1::basic_string`、`__cxxabiv1`（非纯 C）
- **JNI 动态注册**：无 `Java_*` 静态导出符号 → 方法在 `JNI_OnLoad` 里 `RegisterNatives` 注册

---

## 5. 策略判定（protocol-signature-reverser Phase 3）

| 判据 | 结论 |
|------|------|
| 签名绑定设备密钥？ | ✅ 是（Android Keystore ECDSA + Part1 设备恒定） |
| 签名绑定会话态？ | ✅ 是（Part2 每次启动变化） |
| 纯离线还原可行？ | ❌ 否（硬件密钥不可提取 + 会话态） |
| 对应失败模式 | SF-013（生命周期/设备绑定签名） |
| **选择策略** | **E：Frida RPC 在线签名**（设备在线，直调 native 函数当 oracle） |

> 与淘宝 MTOP / 抖音八神同类：签名绑设备+会话，**离线 unidbg 同样产不出合法签名**，最省力的是在线 oracle。

---

## 6. 策略 E 落地（已验证）

### 6.1 Frida RPC oracle

- Hook 脚本：`projects/ctrip/hooks/sign_rpc.js`
- Python 客户端：`projects/ctrip/scripts/sign_oracle.py`

实测输出（spawn 注入）：

```
sign(03041512b7ae9d31d362cf4566ba4396)
  = C85B162EB3128973D7039908AE2D6AE95EF3926A14E86A77A9E2B48E59D168B0CB3783C4121
```

### 6.2 使用方式

```python
# 1. 设备在线 + frida-server + app 启动（spawn 注入，避免 attach 热注入触发反检测）
# 2. 对任意请求 body 计算 md5：
md5hex = hashlib.md5(body.encode("utf-8")).hexdigest()
# 3. 调 oracle 拿签名：
x_payload_source = script.exports_sync.sign(md5hex)
# 4. 组装请求头（连同 token/label 一并带上）：
#    x-payload-source, x-payload-bnlabel(getToken2), x-payload-bnlabel2(getLabelV2), ...
```

### 6.3 关键坑

- **必须 spawn 注入**：attach 热注入会触发 `libscmain.so` 反检测 → `script has been destroyed`（进程被反检测机制处理）
- **frida-server 需 `-D` 后台 + `adb forward tcp:27042`**，脚本内已用 `os.system` 自建 forward（绕开 adb server 重启丢 forward）
- **RPC 调 Java 需 `Java.perform` 包裹**（否则脚本销毁）；`bnSimpleSign` 是 `synchronized` 方法

---

## 7. 相关产物

| 产物 | 路径 |
|------|------|
| 签名 oracle Hook | `projects/ctrip/hooks/sign_rpc.js` |
| 签名采集 Hook | `projects/ctrip/hooks/capture_sign.js` |
| oracle 客户端 | `projects/ctrip/scripts/sign_oracle.py` |
| 采集启动脚本 | `projects/ctrip/scripts/run_sign_capture.py` / `run_sign_attach.py` |
| native so | `projects/ctrip/so_analysis/libscmain.so` |
| 签名样本 | `projects/ctrip/capture/sign_capture.log` |

---

## 8. 后续（可选）

- 若需**离线**：对 `libscmain.so` 的 `simpleSign` 做 IDA 深度分析（RegisterNatives 表 → 定位函数偏移 → 还原
  Part3 的 keyed 运算）。但即使还原了算法，**设备密钥仍在 Android Keystore 硬件内**，离线仍无法产签名
  （SF-013），故不推荐投入。
- 若需**跨设备**：每台新设备需重新获取其 Part1（设备密钥指纹），Part2/Part3 依赖该设备运行态，
  故签名本质是「每台设备一个在线 oracle」。

---
*生成时间：2026-08-28 · skill: protocol-signature-reverser（策略 E）*

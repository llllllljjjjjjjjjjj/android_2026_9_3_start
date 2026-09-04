---
name: android-recon
description: Android 逆向「侦察与静态分析」总入口。负责拿到 APK 后的第一阶段：设备连接（真机优先 Pixel 4 / MuMu fallback）、证书持久化（含 Android 14 APEX CA）、jadx/apktool 反编译、API/调用链提取（接 reverse_index 索引）、抓包治理（代理端口校准/SSL Pinning 初判/r0capture/proxy 残留/机场上游链/QUIC/eCapture/fp_stack 指纹传输）、APK malformation 修复，并把任务路由到脱壳/动态/签名三个专项 skill。触发词：APK反编译、提取API、调用链追踪、jadx、apktool、连真机、连模拟器、MuMu、证书持久化、抓包、抓不到包、真机没网、代理残留、机场、QUIC、fp_stack、eCapture、malformation、Android逆向入口。
whenToUse: 用户提到 APK 反编译、提取 API、jadx、apktool、连真机/模拟器、证书持久化、抓包、QUIC、malformation 或任何 Android 逆向入口任务时
---

# Android Recon — 侦察与静态分析（逆向总入口）

## 角色与边界

你是 Android 逆向的**第一道工序**。本 skill **只做**：设备/环境就绪、静态反编译与 API 提取、抓包通路打通、任务分诊。

> 🔴 **边界（不要越界）**：
> - 遇到「壳」→ 交给 **android-unpack**
> - 需要 Frida Hook / 反检测 / SSL 强绕过 / SO 分析 → 交给 **android-dynamic**
> - 需要还原签名算法 / 纯协议 / unidbg → 交给 **protocol-signature-reverser**

```
拿到 APK
   │
   ├─ jadx 打不开/报错 ────────────→ §1.0 malformation 修复
   ├─ jadx 只有空壳 dex ───────────→ 🔁 android-unpack（脱壳）→ 回到本 skill §2
   ├─ "反编译/提取API/调用链" ─────→ §2 静态分析（接 reverse_index 索引）
   ├─ "连不上设备/证书/抓不到包" ──→ §1 环境 + §3 抓包治理
   ├─ "真机没网/抓完断网" ─────────→ §3.2 proxy 残留排查（高频坑）
   ├─ "要Hook/反检测/分析SO" ──────→ 🔁 android-dynamic
   └─ "还原签名/纯协议/unidbg" ────→ 🔁 protocol-signature-reverser
```

> 🧰 **配套 MCP（无 UI 优先，权威工作流见 [AGENTS.md]）** —— 本 skill = 工作流**阶段 1（采集/侦察）→ 反编译 → 交阶段 2**：
> - 连真机 / 拉 APK / 查组件 / Root 数据：`frida_orchestrator`（`adb_devices`、`adb_connect`、`bootstrap_device_toolchain`、`pull_package_apk`、`package_components`、`root_read_file`、`sqlite_query_root`）。
> - 反编译到 `projects/<target>/decompiled/` 后 → `reverse_index` `index_project` 建索引 → `find_endpoint`/`find_symbol`/`search_strings`/`list_suspicious_sign_methods`（阶段 2）。
> - 抓包代理设/清：`android_proxy_set` / `android_proxy_clear`（**抓完务必 clear，否则 App 断网**，见 §3.2）。
> - 攻坚开工先过 ：`project/<target>/docs/`§1 六项（目标/判官/形态/可证伪/止损/样本）；轻量问答可口头定一句「什么算找到」
---


## 真机基线（Canonical Device）

| 项 | 值 | 说明 |
|----|-----|------|
| 设备 | **Pixel 4 (flame)** | 主力真机 |
| Serial | `9C181EC3BF7E0D` | `adb devices` 确认 |
| 系统 | Android 10 / SDK 29 / arm64-v8a | kernel 5.10.189 |
| SELinux | Enforcing | — |
| Root | **Magisk** | `su`@`/system/bin/su`，toolchain `/data/adb/magisk/` |
| Zygisk | Zygisk | 配合 ZygiskFrida |
| ADB | bundled `android_mcp\toolchain\bin\windows\platform-tools\adb.exe` | 统一入口，MuMu 仅 fallback |
| Frida 主 server | `/data/local/tmp/florida-server` | 16.5.9（Florida 魔改免杀，自报 16.5.10-dev.0） |
| Frida 官方回退 | `/data/local/tmp/f1657` | 16.5.7（官方，重命名运行） |
| Frida 备 server | `/data/local/tmp/frida-server` | 16.7.19（官方） |
| 设备自带工具 | tcpdump / iptables / ip / ss / nc / busybox | **有** |
| 设备缺工具 | strace / curl / wget | **无**；验证网络用 `dumpsys` |

## 工具速查

| 工具 | 路径/调用 | 用途 |
|------|----------|------|
| jadx | `tools\jadx\bin\jadx.bat` | DEX/APK → Java 源码 |
| apktool | `tools\apktool\apktool.bat` 或 `java -jar tools\apktool\apktool_3.0.3.jar` | 解包/重打包、Smali |
| ADB | `android_mcp\toolchain\bin\windows\platform-tools\adb.exe` | 设备通信（MuMu 路径仅 fallback） |
| Frida | venv `.venv-frida-16.5.7`（配 florida-server）/ PC `frida` 16.7.19（配 frida-server） | r0capture / frida-ps |
| objection | 系统 PATH | SSL pinning 一键初判 |
| mitmproxy / Reqable | 系统 PATH；MCP=`reqable` / `charles` | 抓包（弱 pinning；强 pinning 用 mitmproxy 透明） |
| eCapture | 真机 `/data/local/tmp/ecapture` | 内核 TLS 明文（代理检测/国密/QUIC 降级） |
| fp_stack | `projects/fp_stack/` | 真机 CH/JA3/JA4 复刻 + 私有 QUIC 版本拨号（传输墙先过这里） |
| MoveCertificate | 真机 App 1.5.7 | user→system 证书；A14 真路径见 §1.3 |
| Malfixer | `apktool d -f` 复现崩溃定位 / 开源 malfixer | 修复 malformed APK |
| native .so 套件 | `tools\so-reverse\`：rabin2 体检 / Ghidra `ghidraRun.bat` / blutter / Il2CppDumper | native SO 侦察（分层详见 [AGENTS.md](../../../AGENTS.md)；APK/Java 层仍用上面的 canonical jadx/apktool） |

> PowerShell 不支持 `&&`，多命令用 `;`。所有脚本路径相对项目根目录。

---

# §1 环境与设备

## 1.0 反编译前先排除 malformation（2026 新趋势）

jadx 打不开 ≠ 一定加固。3000+ 样本用 malformation（同名目录/文件、损坏 AXML、错误 CRC）使工具崩溃。

```powershell
# jadx 报错先尝试修复，再判断是否真加固；无 malfixer 时用 apktool -f 复现崩溃定位 malformation
apktool d -f target.apk -o apk_unpacked   # 报哪个文件错 → 即 malformation 点
```

## 1.1 真机连接（Pixel 4，优先）

```powershell
$ADB="android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
& $ADB devices                                   # 确认 9C181EC3BF7E0D device
& $ADB shell "su -c '/data/local/tmp/florida-server -D &'"   # 起魔改 frida（Florida 16.5.9，当前主力，root）
# 官方回退（16.5.7）：& $ADB shell "su -c '/data/local/tmp/f1657 -D &'"
& $ADB forward tcp:27042 tcp:27042
.\.venv-frida-16.5.7\Scripts\frida-ps.exe -H 127.0.0.1:27042   # 验证（客户端 16.5.x 配 16.5.x server）
```

> **MCP 一键**：`frida_orchestrator` → `adb_devices` → `bootstrap_device_toolchain`（装算法助手 + 推/起 frida-server）。优先 MCP，避免截图点按。

## 1.2 MuMu 连接（fallback，VM index 陷阱）

MuMu 的 VM index **不一定是 0**，必须逐个确认。仅在无真机时用。

```powershell
& "<MuMuManager.exe>" adb -v 4            # 逐个 index 试 0/1/2/3/4 查 ADB 端口
& "<MuMu>\nx_main\adb.exe" connect 192.168.1.16:5555   # 典型端口
```

| 触发条件 | 一线修复 | 兜底 |
|---------|---------|------|
| `adb connect` 连不上 | `MuMuManager.exe adb -v <0..4>` 逐个查端口 | `info -v <index>` 未启动先 `control -v <index> launch` |
| `frida-ps` 无输出 | 确认 `-D` 后台启动 + 端口转发 | `-H 127.0.0.1:27042` |

## 1.3 证书持久化

Reqable/Charles 大面积 **SSL handshake failure** = CA 没进系统库。A14 真路径是 `/apex/com.android.conscrypt/cacerts/`（旧 `/system/etc/security/cacerts/` 多半 ro 无效）。


**真机（Magisk，优先）**：`MoveCertificate` App 一键把 user 证书提到 system，或 systemless cacerts 覆盖（重启保留）。
1. PC 取 CA：Reqable=`%AppData%/Roaming/Reqable/certificate/reqable-root.crt`；`openssl x509 -inform PEM -subject_hash_old` → 文件名 `<hash>.0`（本机 Reqable 曾为 `cfc5ad71.0`）。
2. 推系统库（MoveCertificate 已把 APEX cacerts 做成 rw）：MCP `root_push_file` → `/apex/com.android.conscrypt/cacerts/<hash>.0`（644, root:root）。
3. 再镜像 `/data/misc/user/0/cacerts-added/<hash>.0`（644, system:system）→ 重启后 MoveCertificate 会重新提升，持久化。
4. `force-stop` 目标 App 再开，让它重读信任库。

> 🔴 **禁止 Git Bash 直 `adb push /data/...`**：MSYS 会把远程 `/data` 转成 `C:/Program Files/Git/data/...`；Magisk `su -c '多行'` 会被拆断。一律用 `frida_orchestrator` 的 `root_push_file` / `adb_root_shell`。

**MuMu（/system 只读，fallback）**：remount 常失败 → tmpfs 覆盖（重启需重做）：

```bash
HASH=$(openssl x509 -inform PEM -subject_hash_old -in cert.pem | head -1)
adb push cert.pem /sdcard/$HASH.0
adb shell "su -c 'cp /sdcard/$HASH.0 /system/etc/security/cacerts/ && chmod 644 /system/etc/security/cacerts/$HASH.0'"
```

## 1.4 Frida 版本矩阵（写脚本/抓包前必读）

| server | 版本 | PC 客户端 | 适用 |
|--------|------|-----------|------|
| `/data/local/tmp/florida-server` | 16.5.9（Florida 魔改免杀，自报 16.5.10-dev.0） | venv `.venv-frida-16.5.7`（**16.5.x↔16.5.x**） | **主力**，改名裸启动 |
| `/data/local/tmp/f1657` | 16.5.7（官方） | venv `.venv-frida-16.5.7`（**16.5.x↔16.5.x**） | 官方回退 |
| `/data/local/tmp/frida-server` | 16.7.19（官方） | PC `frida` 16.7.19 | 普通目标 |

> 🔴 **17.x 在硬目标上全挂**（XHS 所有模式秒退）；16.7.19 / 16.5.x 才是工作线。客户端版本必须与所选 server 对齐。

---

# §2 静态分析

## 2.1 反编译

```powershell
tools\jadx\bin\jadx.bat --deobf --show-bad-code -d <out> <target.apk>   # 推荐
tools\jadx\bin\jadx.bat -Xmx4g --deobf -d <out> <target.apk>            # 大 APK
tools\jadx\bin\jadx.bat --no-res -d <out> <target.apk>                  # 仅代码更快
java -jar tools\apktool\apktool_3.0.3.jar d <target.apk> -o apk_unpacked -f           # Smali 兜底
```

> 🔁 **加壳判断**：jadx 打开后只有几十 KB 空壳 `classes.dex`、类极少 → 转 **android-unpack** 脱壳，脱完回到本节。

## 2.2 识别网络栈（⚠️ 先做这步，决定后续 Hook 方向 / 抓包方案）

```
okhttp3 / OkHttpClient            → 标准 OkHttp（Java Hook 可行，除非有 ART-hook 检测）
cronet / CronetEngine / libcronet → Chromium 栈（XHS/Keeta）→ OkHttp Hook 无效
anet / ANetworkCallImpl / libtnet → 阿里 ANet（Ele.me/淘宝闪购/盒马）→ 不走系统代理/系统 libssl
Mtop / MtopBusiness               → MTOP 协议（签名强校验，见 protocol skill）
libxquic.so / xqc_*               → QUIC 传输（阿里系核心流量）→ 系统代理与 libssl 都旁路
NAL_session_SubmitRequest         → 盒马真实入口（`xqc_h3_send_*` 常 0 触发，别死磕）
TTNet / libttboringssl            → 抖音；代理即断网 → eCapture 零注入（§3.1）
NVNetwork / Shark / libcronet     → 美团系（Keeta/猫眼）私有隧道；裸 HTTPS 边缘常 403
libmtguard.so / mtgsig            → 美团设备令牌（请求无关，见 protocol skill）
retrofit2 / Retrofit              → 标准（注解判加密层，见 protocol skill）
dart:io / HttpClient              → Flutter（走原生 libflutter.so）
```

> ⚠️ **阿里系（ANet+QUIC）警示**：核心 MTOP 走 ANet→`libtnet.so`(内部 BoringSSL)+`libxquic.so`(QUIC)，**完全旁路系统代理与系统 libssl**。表现：Reqable 抓 6 万条请求、0 条 mtop。抓包方案见 §3.4。

## 2.3 结构与调用链（优先用 reverse_index）

```
反编译产物 → projects/<target>/decompiled/
   │
   ├─ reverse_index index_project            # 建索引（首选，秒级全局检索）
   │     ├─ find_endpoint        找 URL/Retrofit/OkHttp 接口锚点
   │     ├─ find_symbol          找 类/方法符号
   │     ├─ search_strings       找字符串字面量
   │     └─ list_suspicious_sign_methods  找疑似签名/加密/token 逻辑
   └─ jadx grep（兜底，索引未覆盖时手工）
```

- Manifest：`package_components`（MCP）或 `Select-String AndroidManifest.xml -Pattern "android:name"`，关注 Launcher Activity / Application / 网络权限。
- 架构：`*Presenter`→MVP；`*ViewModel`+`LiveData/StateFlow`→MVVM；`domain/data/presentation`→Clean。
- 混淆导航：ProGuard/R8 **不改** 字符串字面量、Retrofit 注解、框架类名 → 从字符串/注解搜起，反向追调用方。

```
# API 锚点（index 未覆盖时手工 grep）
@GET|@POST|@PUT|@DELETE|@PATCH    @Query|@Path|@Body|@Field|@Header
Request\.Builder|\.url\(|Interceptor|addInterceptor
https?://[^"]*    api[_-]?key|secret|token|bearer    BASE_URL|API_URL|ENDPOINT
extends Application|onCreate|extends ViewModel|@Module|@Provides|@Inject
```

## 2.4 API 文档格式

```markdown
### `METHOD /path`
- 源文件: com.example.api.ApiService (ApiService.java:42)
- 完整URL / 参数 / 请求头 / 请求体 / 响应
- 调用链: LoginActivity → LoginViewModel → UserRepository → ApiService
```

## 2.5 静态失败处理

| 触发条件 | 一线修复 | 兜底 |
|---------|---------|------|
| jadx 报错/类残缺 | `--show-bad-code` / `-Xmx4g` | 转 apktool Smali 手工 |
| 只出空壳 dex | 确认加固 → android-unpack | 脱壳后回 §2 |
| 搜不到 URL/接口 | URL 被加密/拼接 → 搜 `StringBuilder`/Base64/解密函数 | 转 android-dynamic 运行期 Hook |
| 关键逻辑在 native | 定位 `System.loadLibrary` 的 so | 转 android-dynamic §SO 分析 |
| 反射/动态加载断链 | 搜 `Class.forName`/`getMethod`/`DexClassLoader` | 转 android-dynamic Hook 反射点 |

---

# §3 抓包治理

| 触发条件 | 一线修复 | 兜底 |
|---------|---------|------|
| 抓不到任何包 | **核对代理真实监听端口**（显示端口常与实际不符，如 Reqable 实际 9000） | `netstat -ano` 确认端口 → `android_proxy_set <IP> <真实端口>` |
| 抓到包全密文 | SSL Pinning → `objection -g <包名> explore --startup-command "android sslpinning disable"` | 强 pinning → §3.3 mitmproxy 透明 |
| App 不走系统代理 | **r0capture**（socket 层通杀）：`frida -U -f <包名> -l r0capture.js` | ANet/QUIC → §3.4 libxquic hook |
| **真机突然「没网」（底层 ping/DNS 通）** | **§3.2 proxy 残留排查**（最高频坑） | — |
| 高频请求触发风控 | session 限频 + 轮转 + 用非作者小号 | 切工具（Reqable→mitmproxy）；风控观察 ON 时记 |
| PC 开抓包后机场断 / 出网失败 | **§3.5 机场上游链**（Charles/Reqable 抢系统代理冲掉 OneLite:7892） | OneLite 切 TUN |
| 高频请求触发风控 | session 限频 + 轮转 + 用非作者小号 | 切工具（Reqable→mitmproxy）；**禁刷无效签名**；风控观察 ON 时记 |

## 3.1 抓包方案选择器

```
弱/无 pinning        → Reqable + TrustMeAlready（系统代理+系统证书）
标准 OkHttp pinning  → objection sslpinning disable / JustTrustMe(LSPosed)
强 pinning(XHS 类)   → §3.3 mitmproxy 透明 + iptables REDIRECT（系统代理被拒时）
不走系统代理         → r0capture（socket hook）
ANet/QUIC(阿里系)    → §3.4 Hook 真实入口（盒马=NAL，不是 xqc_h3_send_*）
代理检测/配证书没网  → ecapture（eBPF，内核 TLS 抓明文，不走代理不碰证书）
抖音/代理即断网      → eCapture text --hex 零注入；uid 阻 UDP/443 可逼 QUIC 降 TCP
美团 NV/Shark        → eCapture + attach 解密桥（猫眼 `IIVTQYOSF`；Keeta `d0.result()`）；裸 HTTPS 边缘常 403
传输指纹/私有 QUIC   → §3.6 fp_stack（先过传输墙，再谈签名）
```

## 3.2 真机「没网」= proxy/iptables 残留（最高频坑）

抓包工作会改全局网络配置（`android_proxy_set`、mitmproxy 透明 + iptables）；忘了清 → App 流量倒进死端口 = **表现为没网，但 ping/DNS 仍通**，极易误判为「网络问题」。按序排查：

```bash
adb shell settings get global http_proxy          # ① 最常见元凶；死端口=没网
adb shell su -c "settings put global http_proxy :0"   # 清（或 MCP android_proxy_clear）
adb shell su -c "iptables -t nat -L -n"           # ② 查 REDIRECT/DNAT/8080/8888 透明代理残留
adb shell su -c "ip rule"                          # ③ 策略路由残留
adb shell settings get global airplane_mode_on     # ④ 飞行/wifi
adb shell "ip route get 8.8.8.8; ping -c1 8.8.8.8" # ⑤ 链路层
```

> ✅ **验证用系统判定**（设备无 curl）：`adb shell dumpsys connectivity | grep VALIDATED`。
> ⚠️ 实验室「域名→192.168.2.1」是假设，真机实际在 192.168.1.x 网段；`ping 192.168.2.1` 失败属正常。

## 3.3 强 pinning：mitmproxy 透明 + iptables REDIRECT

系统/WiFi 代理 + 系统证书被强 pinning 拒（XHS 类）→ 唯一可行是透明模式 + 设备侧 iptables 把出站重定向到 mitmproxy 端口（ADB 隧道，设备 WiFi 仍可用）。**仅对强 pinning 用**；普通 App 仍先 Reqable+TM。

## 3.4 ANet/QUIC（阿里系）：Hook libxquic 拿明文

核心 MTOP 走 ANet→QUIC，旁路系统代理与系统 libssl（Reqable 抓 6 万条 0 mtop）。真传输 = `libxquic.so`(QUIC) + `libtb_ssl.so`(BoringSSL，符号带 `tb_` 前缀)。

```
Hook libxquic 的 xqc_h3_request_send_headers / xqc_h3_request_send_body  → 加密前明文 header+body
盒马真实入口 = NAL_session_SubmitRequest（xqc_h3_send_* 常 0 触发，别当没流量）

```
- 纯 native，**不触发 quicksparrow 的 ART-hook 检测**。
- ⚠️ libxquic **后加载**（spawn 冷启后才映射）→ 必须 load 后 re-arm，不能只在 spawn 时挂。
- 协议形状（自由复用）：`POST https://waimai-guide.ele.me/gw/{api}/{ver}/`，body `data=<urlencoded json>&type=originaljson`，appKey `24895413`；server 校验 `md5(raw body)`，body 可自由构造，优先 POST-native 接口（GET-native 会重编码 query 破签名）。
- 阿里 xquic 私有版本 `0xff00001d` = draft-29（salt 必须取 xquic 源码，网上 16B 残值是假的）；美团 MQUIC `0xd4000400` = 私有版本号 + 标准 v1 salt。解密/拨号见 §3.6。

> 🔑 **F-001 铁律**：HTTP 200 ≠ 业务成功。上报类接口完工必须追问「服务端计数真的增加了吗？」（XHS 实测 code=0 仅 fire-and-forget，真账号校验另算）。

---
## 3.5 机场与抓包共存（OneLite :7892）

PC 常驻一梯云 **OneLite**（`127.0.0.1:7892`）。Charles(8888)/Reqable(9000) 都抢 **Windows 系统代理**，后起者覆盖 → 抓包工具直连出网 = 机场被「断」。

**正解 A（首选）**：抓包工具设**上游代理链**到 `127.0.0.1:7892`。
- Charles：`Proxy → External Proxy Settings` → HTTP & Secure 都填 127.0.0.1:7892
- Reqable：设置 → 网络 → 上游/外部代理 → `127.0.0.1:7892`

**正解 B**：OneLite 切 TUN（不动系统代理）。TUN 与抓包环路则回退 A。

手机抓包：WiFi 代理指 PC 的 Charles/Reqable，**不要**手机侧再叠机场（双重代理会环）。抓完设备侧必须 `android_proxy_clear`（§3.2）。

## 3.6 fp_stack：指纹级传输（先过传输墙）

签名过了但裸 `requests`/`curl` 403、QUIC 协商不上、JA3 被拒 → **缺口在传输，不在算法**。入口 `projects/fp_stack/`（`fpstack_client.py` / `replay.signed_fetch`）。

铁律：**指纹一律真机真实 CH/JA3/JA4**，禁止合成生产档案。

已打通（2026-08）：
- H1 手写保序 / H2 Akamai 全控面 / H3 + QUIC 内 CH 级 spec 注入
- 淘宝 ANet/xquic `0xff00001d`=draft-29；美团 MQUIC `0xd4000400`（v1 salt）
- 真网：waimai-guide draft-29 → 网关 `ILEGAL_SIGN`（传输/协议/格式三层已过，剩 SF-013）
- 盒马搜索 / 猫眼 yanchu：真机 Meituan CH + Kernel H1 打通公网 HTTPS（非 NV/Shark）

`x-pv` 真机是 `6.3`（不是 `m-pv`）。推导失败必须显性化，禁止静默默认 QUIC v1。

---

# §4 工具黑名单（实测不可用，按 App/版本复核，勿一刀切）

| 工具 | 失败场景 | 原因 / 改用 |
|------|---------|------------|
| 算法助手 v2.1.2 旧包 | Android 14 「系统服务未启动」 | 用 MCP `bootstrap_device_toolchain` 装 toolchain 自带 1.0.9；配置属主 MCP 已自动 `system:system`（2026-08-18 修，不用再手动 chown；存量 root:root 才需 `chown -R`） |
| Git Bash 直 adb | 推 `/data`/`/apex` | MSYS 毁路径 → MCP `root_push_file` |
| PC frida 17.x | 连 new-server 16.5.8-dev | 协议不兼容 → 只用 `.venv-frida-16.5.7` |
| Reqable + TrustMeAlready | 强 SSL pinning(XHS 类) | 绕不过 → §3.3 mitmproxy 透明 |
| 标准 WiFi 代理 + 系统证书 | 强 pinning / A14 未装 APEX CA | §1.3 + mitmproxy 透明 |
| Java/OkHttp Hook 抓包 | Cronet/HTTPDNS/ANet/NV/Shark | 拦不到核心流量 → 先 §2.2 确认栈 |
| 裸 HTTPS 打美团/Keeta API | Shark/cronet 隧道 | 边缘 403 「.」→ 设备隧道或 fp_stack 复刻 |

---
# §5 任务分诊（路由到专项 skill）

| 用户意图 | 转交 | 入参提示 |
|---------|------|---------|
| 有壳/脱壳/加固/VDEX/360VIP 抹 magic | **android-unpack** | 包名 + APK 路径 |
| Hook/反检测/SSL强绕过/SO/Stalker | **android-dynamic** | 包名 + 已识别网络栈 + so 名 |
| 签名/sign/x-mini/shield/mtgsig/八神/算法还原/unidbg | **protocol-signature-reverser** | 签名位置 + so 文件 + 抓包样本 |
| QUIC 私有版本 / JA3 墙 / 裸请求 403 | **先 §3.6 fp_stack**，再交 signature | 真机 pcap + 档案名 |

---

# 🚨 红线

1. 禁止跳过 malformation 检查就判定「加固」（先 `apktool -f` 复现）
2. 禁止 Hook 前不识别网络栈（先搜 OkHttp/Cronet/ANet/libxquic）
3. 禁止未验证服务端入账就说「上报通了」（F-001）
4. 禁止假定真机/MuMu 已就绪：先 `adb devices` 确认 serial
5. ADB 一律用 bundled `android_mcp\toolchain\bin\windows\platform-tools\adb.exe`（MuMu 仅 fallback）
6. **抓包改了全局代理/iptables，收尾必须 clear**（否则 App 断网，见 §3.2）
7. 开 Charles/Reqable 前必须链机场上游 `127.0.0.1:7892`（§3.5），禁止手机侧再叠机场
8. A14 装 CA 走 `/apex/com.android.conscrypt/cacerts/`，禁止只写旧 `/system/etc/security/cacerts/`
9. 传输墙未过时禁止宣称「签名算法错了」（先 fp_stack / 原版 App 同环境对照）

---

# 项目文件规范（强约束，见 AGENTS.md）

```
projects/<target>/
├── apk/            原始 apk / 拆出 dex
├── decompiled/     jadx / apktool 反编译产物（→ reverse_index index_project）
├── hooks/          项目专属 Frida/hook 脚本
├── scripts/        项目专属 Python
├── so_analysis/    .so + .i64 + IDA 分析
├── capture/        抓包 flows / 日志
├── artifacts/      截图 / 中间产物 / 报告 json
├── docs/           分析笔记 / 进度 / 交接 md
└── README.md       目标说明 + 现状 + 入口（必须有）
```

> 目录名一律 ASCII；不在根目录散落 .py/.js/.apk/截图。


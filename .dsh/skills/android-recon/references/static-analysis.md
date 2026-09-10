# 静态分析（详细操作手册）

> 本文件由 `SKILL.md §2 静态分析` 引用，属于**按需加载**的详细操作层：反编译命令、网络栈识别全表、reverse_index 调用链检索、grep 锚点、API 文档格式、静态失败兜底时读本文件。

---

# §2 静态分析

## 2.1 反编译

优先用 `pull_package_apk`，保留 base 与 split APK 清单。外部 APK 先计算 hash。

```powershell
tools\jadx\bin\jadx.bat --deobf --show-bad-code -d projects\<target>\decompiled\jadx <apk>
tools\apktool.bat d <apk> -o projects\<target>\decompiled\apktool_<timestamp>
```

- jadx 报错：用新 apktool 目录复现，并记录错误；不能直接判加固。
- 仅有 Stub/极少类：以壳特征复核后转 `android-unpack`。
- Java 可读：jadx 追调用链；需精确 Manifest/resources/smali 时再用 apktool，不要求所有任务双跑。
- ZIP 库存同时识别运行时组合：`index.android.bundle`/`.hbc`/`libhermes.so`（React Native/Hermes）、`libflutter.so`+`libapp.so`+`flutter_assets`（Flutter）、`libil2cpp.so`+`global-metadata.dat`（Unity IL2CPP）；单一文件只算候选。
- 离线枚举 APK 内 `.cer/.der/.pem/.crt` 与 `network_security_config.xml`；可解析证书只记录 subject/issuer/有效期/SAN DNS。SAN 只是候选 host，不据此做网络探测或扩域。
- 记录反编译 warnings/failed methods；反编译成功不等于运行期逻辑已证实。

## 2.2 先识别网络栈，再选抓包或 Hook 路径

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
不要把某个 App 的入口或策略泛化为全局规则。网络栈结论要附字符串、类、导入符号或 maps 证据。
> ⚠️ **阿里系（ANet+QUIC）警示**：核心 MTOP 走 ANet→`libtnet.so`(内部 BoringSSL)+`libxquic.so`(QUIC)，**完全旁路系统代理与系统 libssl**。表现：Reqable 抓 6 万条请求、0 条 mtop。抓包方案见 §3.4（traffic-capture.md）。

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
 **索引盲区**（此时才用 grep）:①字符串被 `"si"+"gn"`/`StringBuilder` 拆开 → 单字符串搜不到，改用 `search_code` 正则或搜资源；②硬编码 URL/密钥可能在 `res/values/strings.xml`、`assets/`、`lib/*.so`（不只在 Java 层）
```
# 网络注解与参数 —— Retrofit 声明接口的地方
@GET|@POST|@PUT|@DELETE|@PATCH   @Query|@Path|@Body|@Field|@Header

# OkHttp 链路 —— 请求构造/拦截器（签名常加在拦截器里！）
Request\.Builder|\.url\(|Interceptor|addInterceptor

# UR L 与密钥线索
https?://[^"]*   api[_-]?key|secret|token|bearer   BASE_URL|API_URL|ENDPOINT

# 应用初始化 / DI
extends Application|onCreate   extends ViewModel   @Module|@Provides|@Inject
```

**判定真签名（防误报）**:字段名叫 `sign` 不等于真签名。用 **algo-lab** 看参与字段的**白名单/顺序/编码**，或 **frida 当 oracle 在线验证**；若该 App 走 ANet/QUIC（阿里系，见 §3.4），签名逻辑在 **SO** 而非 Java 拦截器 → 转 android-dynamic / protocol-signature-reverser。



> 📝 **记录前**：风控记录 YES 时，把本次抓包/静态分析得到的**风控对抗素材**记到 `projects/<target>/docs/risk-observations.md`：接口频控表现（请求间隔/批量大小/限流阈值）、403/429 出现时的接口与 IP 上下文、全套请求头与参数完整性、指纹上报接口、埋点链路；**以及清单外任何你认为对抗风控可能用得上的点（哪怕不起眼）**（格式见 SKILL.md 红线 10）。

## 2.4 API 文档格式

```API 记录至少包含 method/path、源文件与行号、参数/headers/body、调用链和未解动态字段。关键词命中、导出组件或 WebView API 只算候选；没有 source→sink 或运行证据时不能升级为结论。
```

## 2.5 静态失败处理

| 触发条件 | 一线修复 | 兜底 |
|---------|---------|------|
| jadx 报错/类残缺 | `--show-bad-code` / `-Xmx4g` | 转 apktool Smali 手工 |
| 只出空壳 dex | 确认加固 → android-unpack | 脱壳后回 §2 |
| 搜不到 URL/接口 | URL 被加密/拼接 → 搜 `StringBuilder`/Base64/解密函数 | 转 android-dynamic 运行期 Hook |
| 关键逻辑在 native | 定位 `System.loadLibrary` 的 so | 转 android-dynamic §SO 分析 |
| 反射/动态加载断链 | 搜 `Class.forName`/`getMethod`/`DexClassLoader` | 转 android-dynamic Hook 反射点 |

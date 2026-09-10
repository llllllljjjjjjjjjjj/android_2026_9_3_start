# 抓包治理（详细方案手册）

> 本文件由 `SKILL.md §3 抓包治理` 引用，属于**按需加载**的详细方案层：proxy 残留排查、mitmproxy 透明、ANet/QUIC Hook、机场共存、fp_stack 指纹传输时读本文件。SKILL.md §3 只保留「触发→一线→兜底」速查决策表与方案选择器。

---

# §3 抓包治理

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

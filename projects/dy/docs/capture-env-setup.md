# 抖音搜索抓包环境准备 SOP（Charles 中间人链路）

> 用途：复现 App 真实搜索请求（url + headers + body + 响应明文），供 PC 复刻 / RPC oracle 比对。
> 核心结论：**PC 直连无论怎么构造都 hit_shark，只有走 App 原生 Cronet 栈（经 Charles 中间人）
> 的请求才被服务器接受**。所以抓包是"拿真值"的唯一可靠途径。
>
> 链路全景：
> ```
> App(Cronet/QUIC)
>   → [quic_downgrade.js]  QUIC(UDP443) 封锁 → 回退 TCP+HTTP/2
>   → Kitsunebi(tun0 VPN, SS 127.0.0.1:8388, aes-128-gcm, pwd=abc12345)
>   → adb reverse tcp:8388 → PC Xray(SS入站8388 → sniffing → SOCKS 127.0.0.1:8889)
>   → Charles(HTTP代理8888 + SSL Proxying + SOCKS 8889)
>   → [dy_hook30_probe.js] custom_verify 回调语义反转(1→0) 绕过 Charles 证书
>   → 服务器
> ```

## 0. 前置资产清单

| 资产 | 位置 | 说明 |
|------|------|------|
| Xray | `D:\Xray-windows-64\xray.exe` | SS 入站 → SOCKS 转发 |
| Xray 配置 | `projects/dy/scripts/xray_ss2charles.json` | SS 8388 → SOCKS 8889 |
| Charles | `D:\charlesproxy\Charles.exe` | 5.2.1，8888 HTTP / 8889 SOCKS |
| Charles 配置 | `C:\Users\lenovo\AppData\Roaming\Charles\charles.config` | SSL Proxying 目标 |
| 手机 Kitsunebi | `fun.kitsunebi.kitsunebi4android` | SS VPN 客户端 |
| QUIC 降级 | `projects/dy/hook_req/quic_downgrade.js` | QUIC→TCP |
| 证书 FORGE | `projects/dy/hooks/dy_hook30_probe.js` | 绕过 Charles 证书 |
| frida server | 设备 `/data/local/tmp/florida-server` | 16.5.9 魔改 |
| frida 客户端 | `.venv-frida-16.5.7` | 16.5.x |

## 1. Xray 配置（已就绪，`xray_ss2charles.json`）

```json
{
  "inbounds": [{
    "tag": "ss-in", "listen": "0.0.0.0", "port": 8388,
    "protocol": "shadowsocks",
    "settings": { "method": "aes-128-gcm", "password": "abc12345", "network": "tcp,udp" },
    "sniffing": { "enabled": true, "destOverride": ["http", "tls"], "routeOnly": false }
  }],
  "outbounds": [
    { "tag": "to-charles", "protocol": "socks", "settings": { "servers": [{ "address": "127.0.0.1", "port": 8889 }] } },
    { "tag": "direct", "protocol": "freedom" }
  ],
  "routing": { "rules": [{ "type": "field", "network": "udp", "outboundTag": "direct" }] }
}
```

要点：SS 入站 8388 与手机 Kitsunebi 的 `127.0.0.1:8388 / abc12345` 对齐；出站 socks 8889 对接 Charles；UDP 走 direct（QUIC 已由 hook 封死，双保险）。

## 2. 手机 Kitsunebi 配置（关键：连本地 127.0.0.1，不是远端）

Kitsunebi 的 SS 服务器必须是 **`127.0.0.1:8388`**（经 `adb reverse` 桥到 PC Xray），
方法 `aes-128-gcm`、密码 `abc12345`。已存配置见
`/data/data/fun.kitsunebi.kitsunebi4android/shared_prefs/*.xml` 的 `core_config_key`。

> ⚠️ 若 Kitsunebi 连的是远端 IP（如 8.133.123.139），App 走的是远端出口，
> **不经 Charles，抓不到包**，且 App 会 -20013（隧道不通/证书问题）。

## 3. Charles 配置（一次性，已固化）

1. **HTTP 代理 8888 + SOCKS 8889**（Proxy → Proxy Settings）。
2. **SSL Proxying 开启**：Proxy → SSL Proxying Settings → 勾选
   `*.amemv.com`（含 `search5-search-m-hj/lf/jh.amemv.com`）。落盘即
   `charles.config` 的 `<sslLocations>` 各 `locationMatch.enabled=true`。
3. **根证书入系统库**：证书 `d18fce22.0`（APatch systemless cacerts，重启不丢）。
4. Web Interface（`control.charles`，供 charles MCP 读取）默认开。

## 4. 启动 SOP（按顺序）

```powershell
# 1) 设备确认 + frida server
adb devices                                        # 9C181EC3BF7E0D
adb shell su -c "nohup /data/local/tmp/florida-server >/dev/null 2>&1 &"

# 2) 隧道（重启后失效，必须重建）
adb reverse tcp:8388 tcp:8388
adb forward tcp:27042 tcp:27042
adb reverse --list && adb forward --list

# 3) PC Xray（后台，窗口保持）
D:\Xray-windows-64\xray.exe run -c projects\dy\scripts\xray_ss2charles.json

# 4) Charles（GUI，需有桌面会话；headless 环境起不来）
D:\charlesproxy\Charles.exe        # 确认 8888/8889 LISTENING

# 5) 手机 Kitsunebi 手动点连接（SS 127.0.0.1:8388）→ tun0 出现即通

# 6) 注入 hook（spawn 模式，QUIC 降级 + 证书 FORGE）
.venv-frida-16.5.7\Scripts\frida.exe -H 127.0.0.1:27042 -f com.ss.android.ugc.aweme ^
    -l projects\dy\hooks\dy_hook30_probe.js        # 证书 FORGE
# QUIC 降级可合并进任一 hook 或单独 -l hook_req\quic_downgrade.js
```

## 5. 验证

- Kitsunebi 连上后：`adb shell ip addr show tun0` 应有 `10.233.233.x/30`；
  `adb shell dumpsys connectivity | grep 'type: VPN'` 见 VPN 网络。
- 手机搜索一次 → Charles 里应出现 `search5-search-m-hj.amemv.com` 明文
  （`hook30` 输出 `[cb] ... 拒绝(1) 被 forge 为通过(0)`）。
- Charles Web Interface 读会话：
  ```python
  import sys; sys.path.insert(0, r'android_mcp\servers\charles_mcp')
  import charles_api as ca
  ca.export_session(port=8888)   # 或 ca.find_entries(port=8888, pattern='general/stream')
  ```

## 6. 关键坑（本轮实测）

| 坑 | 现象 | 解法 |
|----|------|------|
| Kitsunebi 连远端 IP | App -20013、抓不到包 | SS 必须 `127.0.0.1:8388` |
| Charles headless 起不来 | 进程在但无 8888 监听 | 需 GUI 桌面会话；`QT_QPA_PLATFORM=offscreen` 无效 |
| Charles SSL Proxying 关闭 | 走 Charles 仍 hit_shark（CONNECT 隧道，TLS 还是 PC 的） | 改 `charles.config` 的 sslLocations enabled=true |
| 没挂证书 FORGE | 握手失败 lib16/125 | 挂 `dy_hook30_probe.js`（回调 1→0） |
| 没挂 QUIC 降级 | 视频/请求走 UDP 443，过不了 adb reverse 的 TCP 桥 | 挂 `quic_downgrade.js` |
| IDA headless 跑不了 | `Fatal registry error: 拒绝访问` / exit 2 | 需要 `danger-full-access` 权限（注册表访问被 sandbox 拦） |
| App 反枚举 | frida 进程表看不到 aweme | `adb shell pidof` 拿 pid 直连 attach |

## 7. 与 PC 复刻的关系

抓到的 App 真实请求（url+headers+body）是「真值」：
- **body** = zstd 压缩的 form-urlencoded（`x-bd-content-encoding: zstd`），关键参数
  keyword/count/cursor/filter_selected/search_session_id；
- **headers** 含动态头（`x-tt-trace-id`/`x-tt-dt`/`compressed-bcm-chain`/`x-ss-stub`），
  每次请求变化，**离线无法复现**；
- **八神头** = `libmetasec_ml.so+0x28065c` 生成（`hooks/dy_hook21.js` oracle）。

PC 复刻（方向 A）的正确姿势 = charles body 模板 + App 实时 headers + 28065c oracle 签名。

# 环境与设备（详细操作手册）

> 本文件由 `SKILL.md §1 环境与设备` 引用，属于**按需加载**的详细操作层：连真机/模拟器、证书持久化、Frida 版本对齐、malformation 排查时读本文件。SKILL.md 只保留真机基线表与连接要点。

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



## 1.2 证书持久化

系统 CA 信任库路径**按 Android 代次**区分，别一概用 A14 的 APEX：
- **Android 14+**：`/apex/com.android.conscrypt/cacerts/`（APEX 版 CA store，替代旧 /system 路径）
- **Android 10–13（本机 Pixel4/A10 适用）**：`/system/etc/security/cacerts/`（就是系统 CA store，被 Magisk 挂成**只读 tmpfs**）

> ⚠️ 本机是 **A10**，**没有** `/apex/com.android.conscrypt/cacerts/`。系统 CA store 实测在 `/system/etc/security/cacerts/`（139 个 `.0`），为 Magisk 只读 tmpfs + 每证书 ro bind-mount，**直接 `cp` 落地不持久**。本机可靠机制 = **`movecert` Magisk 模块**（见下）。


**本机真机机制 = `movecert` Magisk 模块（不是 APK App）**：已装 `yochananmarqos` Move Certificates v1.9（`id=movecert`，`/data/adb/modules/movecert/`）。其 `post-fs-data.sh` 开机自动把 `/data/misc/user/0/cacerts-added/*` 搬进 `$MODDIR/system/etc/security/cacerts/`（`chown 0:0` + `chcon system_file`），再由 Magisk overlay 到 `/system/etc/security/cacerts/` → 系统信任、重启保留、无「Network may be monitored」警告。

**真机（Magisk，优先）**：
1. PC 取 CA：Reqable=`%AppData%/Roaming/Reqable/certificate/reqable-root.crt`；`openssl x509 -inform PEM -subject_hash_old` → 文件名 `<hash>.0`（本机 Reqable 曾为 `cfc5ad71.0`）。
2. 放 CA：从 Android「信任的凭据」安装，或 MCP `root_push_file` 直推到 `/data/misc/user/0/cacerts-added/<hash>.0`（644, system:system）。
3. 重启（或手动跑 `post-fs-data.sh`）：`movecert` 模块自动搬进 `/data/adb/modules/movecert/system/etc/security/cacerts/<hash>.0`（0:0）。当前模块已含 1 个 `d18fce22.0`。
4. `force-stop` 目标 App 再开，让它重读信任库。

> 🔴 **禁止 Git Bash 直 `adb push /data/...`**：MSYS 会把远程 `/data` 转成 `C:/Program Files/Git/data/...`；Magisk `su -c '多行'` 会被拆断。一律用 `frida_orchestrator` 的 `root_push_file` / `adb_root_shell`。

**MuMu（/system 只读，fallback）**：remount 常失败 → tmpfs 覆盖（重启需重做）：

```bash
HASH=$(openssl x509 -inform PEM -subject_hash_old -in cert.pem | head -1)
adb push cert.pem /sdcard/$HASH.0
adb shell "su -c 'cp /sdcard/$HASH.0 /system/etc/security/cacerts/ && chmod 644 /system/etc/security/cacerts/$HASH.0'"
```

## 1.3 Frida 版本矩阵（写脚本/抓包前必读）

| server | 版本 | PC 客户端 | 适用 |
|--------|------|-----------|------|
| `/data/local/tmp/florida-server` | 16.5.9（Florida 魔改免杀，自报 16.5.10-dev.0） | venv `.venv-frida-16.5.7`（**16.5.x↔16.5.x**） | **主力**，改名裸启动 |
| `/data/local/tmp/f1657` | 16.5.7（官方） | venv `.venv-frida-16.5.7`（**16.5.x↔16.5.x**） | 官方回退 |
| `/data/local/tmp/frida-server` | 16.7.19（官方）⚠️ 本机未部署 | PC `frida` 16.7.19 | 普通目标（需先 push） |

> 🔴 **17.x 在硬目标上全挂**（XHS 所有模式秒退）；16.7.19 / 16.5.x 才是工作线。客户端版本必须与所选 server 对齐。

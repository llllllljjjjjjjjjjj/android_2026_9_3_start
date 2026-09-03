---
name: android-unpack
description: Android 脱壳与加固破解专项。负责「壳识别 → 策略选择 → 脱壳执行 → DEX/SO 验证」。支持 360/腾讯/百度/梆梆/爱加密/网易易盾等商业加固；提供 Frida 动态脱壳、Root 内存提取、抽取壳 frida 主动调用 dumper、内存快照、反调试绕过、VDEX 提取、以及运行期解密壳的 native SO 代码段脱密（梆梆/爱加密）。触发词：脱壳、加固破解、DEX提取、SO脱密、壳识别、VDEX、爱加密、梆梆、360加固、腾讯加固、网易易盾、Root内存提取、抽取壳、FART、Youpk、BlackDex、主动调用。
whenToUse: 用户提到脱壳、加固破解、DEX 提取、SO 脱密、壳识别、VDEX、抽取壳、FART、Youpk、BlackDex、Root 内存提取时
---

# Android Unpack — 脱壳与加固破解

## 角色与边界

你是脱壳专项。**只做** 一件事：把加固 APK 的真实 DEX（或运行期解密的真实 SO 代码段）取出来并验证。

> 🔴 **边界**：
> - 反编译脱壳后的 DEX、提取 API → 回到 **android-recon**
> - 反调试/反 Frida 是为脱壳服务时在本 skill 处理；若是为「运行期 Hook 业务逻辑」服务 → 交 **android-dynamic**
> - 还原签名算法 → **protocol-signature-reverser**

```
加固分析（壳识别/级别评估）→ 策略选择 → 脱壳执行（Frida动态/Root内存/抽取壳主动调用/SO脱密/快照）→ DEX/SO 验证 → 🔁 android-recon
```

> **脚本目录**：`.dsh/skills/android-unpack/scripts/`。ADB 统一 bundled `android_mcp\toolchain\bin\windows\platform-tools\adb.exe`（MuMu 仅 fallback）。PowerShell 多命令用 `;`。

> 🧰 **配套 MCP（无 UI 优先，工作流见 [AGNETS.md]）** —— 脱壳处于工作流**阶段 1↔2 之间（有壳时）**：用 `frida_orchestrator` 起 frida-server（`start_patched_frida_server`，主力魔改 florida-server；官方 f1657 回退见 android-dynamic §3.4）、拉内存 dump 与脱出的 dex/so（`root_pull_file`/`root_read_file`）、取壳样本（`pull_package_apk`）、查壳配置（`sqlite_query_root`）。脱壳产物 → `projects/<target>/apk/`，反编译后回 **android-recon** 建索引。

---

## 工具速查

| 脚本 | 用途 |
|------|------|
| `apk_protection_analyzer.py` | 加固类型识别、保护级别（LOW/MEDIUM/HIGH/EXTREME）、推荐策略、预期成功率 |
| `unpack_orchestrator.py` | **一键编排**：自动分析→选策略→执行（推荐首选） |
| `enhanced_dexdump_runner.py` | Frida 动态脱壳（`--deep-search` 深搜更多 DEX；配合抽取壳主动调用） |
| `root_memory_extractor.py` / `_enhanced.py` | Root 内存静态提取（绕过应用层检测，95%+） |
| `memory_snapshot.py` | 内存快照攻击（检测 Frida 即崩溃时） |
| `antidebug_bypass.py` | 反调试绕过（Java/Native/System 三层） |
| `bangcle_bypass_runner.py` / `.js` | 梆梆专用绕过 |
| `frida_memory_scanner.js` | Frida 内存扫描 |
| `tools\so-reverse\linxerunpacker\linxerUnpacker.exe` | **裸 ELF / 自解壳脱壳**（native）：ptrace/memfd dump + PT_LOAD 重建（arm64 真机 + root）。脱出的 .so 用 `tools\so-reverse` 的 Ghidra/radare2 分析（已就位） |

---

# 阶段 1：壳识别

```powershell
python .dsh\skills\android-unpack\scripts\apk_protection_analyzer.py --apk <target.apk> --verbose
# 或开源 APKiD：apkid <target.apk>
```

| 壳厂商 | 特征 so | 包名特征 | 推荐策略 |
|--------|--------|---------|---------|
| 腾讯乐固 | `libtup.so`/`libshell.so` | `com.tencent.StubShell` | Frida 优先，Root 备选 |
| 360 加固 | `libjiagu.so`/`libprotect.so` | `com.stub.StubApp` | Frida 优先，Root 备选 |
| 百度加固 | `libbaiduprotect.so` | `com.baidu.protect` | Frida |
| 阿里聚安全 | `libmobisec.so` | `com.aliyun` | Root 内存提取 |
| 梆梆加固 | `libDexHelper.so`/`libzhangxin*.so` | `com.secneo.apkwrapper`、`__b_a_n_g_/c_l_e__` 符号 | **Root 首选** + SO 脱密(§4) |
| 爱加密 | `libexec.so`/`libexecmain.so`/`libmsec.so` | `s.h.e.l.l.` | **Root 首选**（零注入）+ SO 脱密(§4) |
| 网易易盾 | VDEX 格式 | — | **Root + VDEX 提取** |
| 抽取壳(二代) | 类完整但方法体 `nop`/`return` | 运行时回填 CodeItem | **策略D 主动调用**(§2.4) |
| 无加固 | DEX 大、类完整 | — | Frida 即可 |

**快速判断**：jadx 打开只有空壳 `classes.dex`（几十 KB）→ 整体壳；类结构完整但方法体空 `nop`/`return` → **抽取壳**（被动 dump 取不到，必须主动调用）。

---

# 阶段 2：脱壳执行

## 2.1 环境准备（真机 + 魔改 frida）

```powershell
$ADB="android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
& $ADB devices                                  # 确认 Pixel 4 9C181EC3BF7E0D
& $ADB shell su -c "echo root_ok"               # Root 策略需要
# 优先 MCP：frida_orchestrator → start_patched_frida_server（自动起魔改 florida-server + root 运行）
# 手动推送自备魔改 frida-server（反 Frida 壳扫进程名时必须改名）：
& $ADB push <你的 frida-server 路径> /data/local/tmp/florida-server
& $ADB shell "su -c 'chmod 755 /data/local/tmp/florida-server; nohup /data/local/tmp/florida-server -D &'"
```

> 🔑 反 Frida 壳扫进程名匹配 `frida`/`server` → 重命名（如 `sysmon_svc`）后裸启动存活；frida-server **必须 root 运行**（否则 ptrace 注入失败）。

## 2.2 策略选择

```
无加固/基础（95%+）              → 策略A Frida 动态脱壳（最快）
360/腾讯/百度（85-95%）          → 策略A 首选，策略B Root 备选
爱加密/梆梆/网易易盾（10-50%）    → 策略B Root 内存提取首选（95%+，零注入）
强反调试/秒崩                   → 策略C 内存快照；先跑 antidebug_bypass
抽取壳（方法体运行时回填）        → 策略D frida 主动调用（被动 dump 无效）
运行期解密 native 壳（SO 代码段）  → §4 SO 脱密（dd 解密段）
无 Root 设备                   → BlackDex 免 Root 脱壳
```

> ⚠️ **被动 dump vs 主动调用**：策略B（被动 `dd /proc/pid/mem`）对**整体壳**有效；对**抽取壳无效**——方法体未调用前不在内存（CodeItem 是 nop/return，运行时壳才回填）。抽取壳必须走策略D。

```powershell
# 一键编排（推荐）
python .dsh\skills\android-unpack\scripts\unpack_orchestrator.py --package <包名> --apk <target.apk> --verbose
# 策略A Frida
python .dsh\skills\android-unpack\scripts\enhanced_dexdump_runner.py --package <包名> --deep-search --verbose
# 策略B Root 内存（绕过商业加固，零注入）
python .dsh\skills\android-unpack\scripts\root_memory_extractor.py --package <包名> --output ./dex_output --verbose
# 策略C 内存快照
python .dsh\skills\android-unpack\scripts\memory_snapshot.py --package <包名>
# 梆梆专用
python .dsh\skills\android-unpack\scripts\bangcle_bypass_runner.py --package <包名> --verbose
```

**Root 内存原理（策略B）**：`/proc/<PID>/maps` 定位 `anon:dalvik-DEX data` → `dd if=/proc/<PID>/mem` 读取 → 合并裁剪到精确 DEX 大小 → 验证结构。不使用 Frida 脚本，完全绕过应用层检测。

## 2.3 策略 D：抽取壳 frida 主动调用 dumper（复用魔改 frida，不刷 ROM）

被动 dump 对抽取壳无效。用魔改 frida 枚举全部类、强制 resolve 触发壳回填方法体，再 dump（FRIDA-DEXDump `deep` 模式 / frida-fart 思路，纯 frida）：

```javascript
// 抽取壳主动调用：枚举已加载类 → 强制 resolve/初始化 → 壳在此回填 CodeItem
Java.perform(function () {
  var classes = Java.enumerateLoadedClassesSync();
  console.log("[*] classes:", classes.length);
  classes.forEach(function (name) {
    try {
      var cls = Java.use(name);
      cls.class.getDeclaredMethods();   // 触发 ArtMethod resolve（壳回填方法体）
      cls.class.getDeclaredConstructors();
    } catch (e) {}
  });
  console.log("[*] resolve done → now dump");
});
// 回填后再跑 enhanced_dexdump_runner.py --deep-search dump 出完整 DEX
```

> 与策略B 正交：先主动调用回填 → 再 dump。dump 出的抽取壳 DEX 常需 **CodeItem patch-back**（把回填的方法体写回 dex CodeItem offset）jadx 才能解，参考 FART repair 阶段。

## 2.4 失败分支

| 触发条件 | 一线修复 | 兜底 |
|---------|---------|------|
| Frida 脱壳被检测崩溃 | 先 `antidebug_bypass.py --protection-type strong_antidebug` | 改策略B Root 内存 |
| 提取 DEX 空/损坏 | 内存加密 → 策略C 内存快照 | 静态分析加密配置 |
| 抽取壳：方法体为空 `nop`/`return` 但类结构完整 | **策略D 主动调用** + CodeItem patch-back | FART/Youpk 改 ROM |
| 爱加密级：spawn 启动期 SIGKILL、attach 崩 frida-server | **策略B Root 内存 dump 零注入**（不触发反 Frida） | ZygiskFrida（见 android-dynamic） |
| native 壳：JNI 符号 is_function=false、字节高熵 | 运行期解密 → **§4 SO 脱密** | — |
| x86_64 模拟器跑 360 加固白屏卡死 | **换 ARM 真机**（libjiagu 经 libnb.so 翻译触发 VMP/反调试轮询卡死 `StubApp.attachBaseContext()`） | 真机脱壳 |
| 网易易盾 VDEX | Root + VDEX 提取（vdex027，滑窗搜全部嵌入 DEX） | — |

---

# §3 DEX 验证

```powershell
tools\jadx\bin\jadx.bat -d dex_verify <extracted.dex>                          # 单个
tools\jadx\bin\jadx.bat -d merged_out classes.dex classes2.dex classes3.dex    # 多 DEX 合并
```

验证通过（类完整、无 stub、方法体非空）→ 🔁 回到 **android-recon** 做静态分析。

---

# §4 SO 代码段脱密（运行期解密壳：梆梆 / 爱加密 native）

很多壳不抽 DEX 而是把 **native .text 磁盘加密**，运行期 packer 解密到内存可执行段。目标是把解密后的代码段 dump 回填进 IDA。

## 4.1 先认准已解密段

`/proc/<pid>/maps` 看目标 SO 段权限：**rwxp / r-xp = 已解密可 dump**（对比磁盘高熵 = 加密）。匿名可执行段才是解密后 .text。

## 4.2 梆梆 SO 脱壳（libzhangxin/libDexHelper 类）

特征：`__b_a_n_g_/c_l_e__` 符号 + maps 反调试 + 代码段运行时解密。

```bash
# 1) 真机跑起目标进程，代码段映射为 rwxp（offset 0，size 如 0xE4000）
# 2) ★ PC 端算好十进制 skip（防 shell 32-bit 溢出，见 4.4）
# 3) dd 解密代码段
adb shell su -c "dd if=/proc/<pid>/mem of=/data/local/tmp/seg.bin skip=<base/4096 十进制> count=<size/4096> bs=4096"
# 4) 覆盖磁盘 SO 前 N 字节 → IDA 改段权限 r→rx + add_func 重建（见 4.5）
```

## 4.3 爱加密 SO 脱密（libmsec/libjni-encrypt-rsa 类，零注入）

.text 磁盘加密，运行期 mremap 解密到**匿名 r-xp 段**。root `dd /proc/pid/mem` **被动** dump 解密段（零注入，不触发反 Frida）→ 回填 IDA。

> ⚠️ **SHIFT 对齐坑**：libjni-encrypt-rsa 实测 **SHIFT=0，IDA vaddr 直对 dump 偏移**（切勿套用 0x18000）。先在 maps 认准匿名 r-xp 段（如 `6de8c41000-6de8c7b000`）才是解密后 .text。

## 4.4 ★ shell dd 大地址 32-bit 溢出坑（高频，必中）

Android sh 的 `$((0x6de4c4e000))` / `$((base/4096))` 是 **32 位运算**，大 VA 地址必溢出算错 skip → dump 到错误内容。

```
解：在 PC 端（64 位）算好十进制 skip 再传给设备 dd；或用 ${base%000} 字符串裁剪避免算术。
凡 dump 高 VA 地址段（0x6d.. / 0x7d..）都中招。
```

## 4.5 IDA 段权限修复 + 多实例坑

dumped SO 段常 r--（无执行位）→ Hex-Rays 不反编译。用 ida-pro-mcp `py_eval`：

```python
import ida_segment, ida_funcs
for ea in range(ida_segment.get_first_seg().start_ea, ...):
    seg = ida_segment.getseg(ea)
    seg.perm |= ida_segment.SEGPERM_EXEC      # r → rx
ida_funcs.add_func(start, end)                # 重建入口函数
```

> ⚠️ **ida-pro-mcp 多实例串 idb**：多个 IDB 同开时 save/操作会跑去别的 idb。每次动手前 `select_instance(<port>)` + `server_health` 核对当前 idb。

---

# §5 实战案例（已验证，可复用）

```
CASE lianxin 梆梆 (libzhangxin.2.so): 运行期代码段 rwxp → dd 内存 dump 脱壳 → 覆盖磁盘 SO →
     IDA 段权限修复，完整解出 Content-CKey(RSA/PKCS1) + body(AES-ECB-PKCS5) 加密链，字节级通。
     → 加密还原细节见 protocol-signature-reverser 案例速查。 | grounding: lianxin_so_unpack_crypto

CASE ct_client 爱加密 (libexec.so/libmsec.so): RASP 级 = raw-svc watchdog + 匿名 rwx 检测 + 反 ptrace。
     spawn → 启动期 SIGKILL；attach → 崩 frida-server 本体（florida 和 new-server 都崩，App 反而存活）。
     ★ 正解 = root 内存 dump 零注入（不触发反 Frida）；frida 注入对此壳走不通（及时止损）。
     | grounding: ct_client_antifrida
```

---

# 加固成功率参考

| 加固 | Frida | 增强Frida | Root内存 | 推荐 |
|------|-------|-----------|----------|------|
| 无加固 | 98% | 98% | 95% | Frida |
| 360/腾讯 | 75-80% | 80-90% | **95%+** | Frida 优先，Root 备选 |
| 百度 | 85% | 90-95% | **95%+** | Frida |
| 爱加密 | 30-50% | 70-85% | **95%+** | **Root 零注入首选** |
| 梆梆 | 10-20% | 50-65% | **90%+** | Root 首选 + SO 脱密 |
| 网易易盾 | 0-10% | 15-25% | **85%+（+VDEX）** | Root+VDEX |
| 抽取壳 | 主动调用 60-85% | — | 被动 dump **无效** | **策略D 主动调用** |

---

# 🚨 红线

1. 禁止在 x86_64 模拟器死磕 360 加固（换 ARM 真机）
2. 抽取壳禁止只做被动内存 dump（必须策略D 主动调用回填）
3. 提取 DEX 必须 jadx 验证后才算成功（类完整 + 方法体非空）
4. 商业加固优先 Root 内存（>动态注入）——**例外：抽取壳被动 dump 取不到方法体，需策略D**
5. ADB 统一 bundled `android_mcp\toolchain\bin\windows\platform-tools\adb.exe`（MuMu 仅 fallback）
6. dump 高 VA 地址段一律 PC 端算十进制 skip（防 shell 32-bit 溢出）
7. 反 Frida 壳：frida-server 必须改名 + root 运行；爱加密级别优先零注入 Root dump

---

# 文件结构

```
.dsh/skills/android-unpack/   （含全部脱壳脚本）
├── SKILL.md                  # 本文件（name: android-unpack）
├── scripts/                  # 10+ 脱壳脚本（见工具速查）
│   └── i18n/                 # zh-CN / en-US 日志
├── README.md / QUICK_START.md / SECURITY.md / _meta.json
```

# 安全提醒
仅用于授权安全研究、自有应用调试、恶意软件分析、教育/CTF。禁止未授权分析、破解付费授权、侵犯隐私。详见 SECURITY.md。

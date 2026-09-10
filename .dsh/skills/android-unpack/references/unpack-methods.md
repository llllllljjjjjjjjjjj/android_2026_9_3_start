# 脱壳执行方法（详细手册：策略 A/B/C/D）

> 本文件由 `SKILL.md 阶段 2：脱壳执行` 引用，属于**按需加载**层：环境准备、四类脱壳策略的完整命令与代码、Root 内存原理、抽取壳主动调用、失败分支兜底时读。先用 SKILL.md 的策略选择器定级，再到本文件取对应命令。

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
运行期解密 native 壳（SO 代码段）  → §4 SO 脱密（dd 解密段，见 so-decryption.md）
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
| native 壳：JNI 符号 is_function=false、字节高熵 | 运行期解密 → **§4 SO 脱密**（见 so-decryption.md） | — |
| x86_64 模拟器跑 360 加固白屏卡死 | **换 ARM 真机**（libjiagu 经 libnb.so 翻译触发 VMP/反调试轮询卡死 `StubApp.attachBaseContext()`） | 真机脱壳 |
| 网易易盾 VDEX | Root + VDEX 提取（vdex027，滑窗搜全部嵌入 DEX） | — |

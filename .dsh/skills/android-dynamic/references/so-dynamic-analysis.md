# SO 动态分析 + 注册级完整性检测（详细手册）

> 本文件由 `SKILL.md §5 SO 动态分析`、`§6 注册级完整性检测清单` 引用，属于**按需加载**层：CFF 反混淆（D-810）、Unicorn 运行期快照、send() 二进制 dump、注册/登录完整性 6 层审计时读。SO 算法要还原成离线纯算/frozen blob → 转 protocol-signature-reverser。

---

# §5 SO 动态分析

🔴 **CHECKPOINT：CFF/虚拟化加固的 SO，禁止 `Interceptor.attach` 改代码页，必须用 Stalker trace 或运行期快照。**

| 触发条件 | 一线 | 兜底 |
|---------|------|------|
| attach 到 CFF 代码页后闪退 | 改 **Stalker** 指令级 trace（不改原代码页） | — |
| Stalker 地址配 Unicorn/hook 对不上 | Stalker 偏移有固定偏差（曾观测 +0x79），**一律以 IDA/objdump 静态绝对地址为准** | IDA 反汇编核对 |
| RDTSC/anti-tamper 时序检测 | CFF 的 RDTSC 多为 `TSC%N` 确定性计算（Apple 单站点 `TSC%3`），**注入正确值/暴力枚举 mod-N** | trace+replay 正确 dispatch |
| 符号全 strip | IDA + 动态 Hook + ida-pro-mcp AI 辅助 | r2frida 动态 |
| 模拟器偏移全错 | **arch-mismatch**：模拟器可能加载不同 ABI（Apple Music MuMu 加载 x86_64 非 arm64-v8a，偏移全不同）→ 先确认进程实际映射哪个 `lib/<abi>/` | — |

## 5.1 D-810 CFF 反混淆（IDA Pro 插件）

`plugins\d810\` → Pseudocode 窗口 `Ctrl+Shift+D` → 选 Control Flow unflatten 规则。

```
模块（optimizers/microcode/flow/flattening/）：
  unflattener.py            OLLVM
  unflattener_indirect.py   BR X8/X11 间接跳转
  unflattener_switch_case.py / unflattener_hodur.py / unflattener_fake_jump.py
dispatcher_detection.py：6 策略（HIGH_FAN_IN / STATE_COMPARISON>0x10000 / LOOP_HEADER /
  PREDECESSOR_UNIFORMITY / CONSTANT_FREQUENCY / BACK_EDGE）
适用：OLLVM / BR_X11 / Hodur / Tigress
```

> ⚠️ **LIMITS**：D-810 对**自定义分布式代码虚拟化**失败（Apple FairPlay SAP：handler 碎片在函数外、table 驱动、stack-address-keyed 状态），对 **`MOV PC,Rx` 间接跳转** flattening 也无效（XHS 实测）→ 退 runtime 快照+Unicorn 或 Frida RPC oracle。
> 跨函数不透明尾调用（`sub_X()+52; BR X1`）`default.json` 不内联 → 换 `default_indirect_resolution` / `identity_call` 或动态 trace。

**无 UI 激活**（ida-pro-mcp `py_eval`，不必 Ctrl+Shift+D）：

```python
import gc, importlib, pkgutil
st = [o for o in gc.get_objects() if type(o).__name__ == "D810State"][0]
# 打包 bug：不 walk 则 InstructionOptimizer.registry 空 → KeyError chainoptimizer
import d810.optimizers as O
for mi in pkgutil.walk_packages(O.__path__, O.__name__ + "."):
    try: importlib.import_module(mi.name)
    except Exception: pass
st.load_project("default.json")   # 或 default_unflattening_ollvm / default_indirect_resolution
st.start_d810()
# 看效果必须清缓存：ida_hexrays.mark_cfunc_dirty(ea) 再 decompile
```

## 5.2 Unicorn 运行期快照（CFF/opaque-token SO 的离线复算）

```
1) runtime mem-dump hook：dump 3 段 + 全部触及堆 + sign I/O → runtime_snapshot.json
   （Apple v9：1.8MB / 203 heap regions）
2) ★ .data.rel.ro 要在重定位之后 dump（用固定指针，不读文件）
3) dumped session/blob 含运行时指针 → 调目标函数前重定位进 Unicorn 映射
```

> **opaque-token 不可 deref**：非规范地址的 handle（Apple SAP RDI=0x1f2a04f6aec30 x86_64）且跨调用恒定 = CFF lookup table 的 opaque token，不是指针（Frida deref 抛 access violation）。含义：只模拟 sign 函数不够，lookup table 在 init+exchange 时构建 → 必须快照 CFF .bss/.data 运行时态，或模拟完整 init+exchange+sign 链。

## 5.3 send()-based 二进制 dump

设备侧 FileWriter 是瓶颈时（大/二进制 SAP/session/heap blob、权限），用 Frida `send()` 流式传到 host receiver，不在设备落盘（Apple SAP dump 死锁正是 send() 破的 → 拿到 3 组完整 SAP 会话）。任何要落盘的二进制 dump 都优先 send()/RPC。

**Hook 入口模板**：
```javascript
var addr = Process.findModuleByName("libtarget.so").findExportByName("JNI_OnLoad");
Interceptor.attach(addr, { onEnter: function(args){ console.log("[+] JNI_OnLoad JavaVM:", args[0]); }});
```

> 无 IDA Pro 时用 Ghidra；r2frida 把 radare2 接到运行中进程。
> 🔁 SO 算法要**还原成离线纯算/frozen blob** → 转 **protocol-signature-reverser**。

---

# §6 注册级完整性检测清单（reusable 6 层审计）

注册/登录页硬失败时，按层排查（Apple Music 实证，注册页强制 `isIntegrityVerificationNeeded=true`）：

| 层 | 检测 | 绕过 |
|----|------|------|
| L1 | Root/模拟器 Java 检查（`Build.PRODUCT/HARDWARE`/test-keys、`/system/xbin/su`、bitmask bit0=emu/bit1=root/bit2=debugger） | hook 这几个方法返回干净值 |
| L2 | Google Play Services 可用性（≥12451000） | hook → 可用 |
| L3 | Play Integrity API（prepareIntegrityToken；token 在全局 volatile） | hook `getIsIntegrityVerificationNeeded()`→false，或供真 token |
| L4 | **服务端 token 校验（Google 签名，不可伪造）** | root/emu/区域被拒 → 需**真机/认证设备**的 token |
| L5 | WebView JS-bridge 指纹（telephony/carrier/store-platform） | hook bridge |
| L6 | 网络签名（X-Apple-ActionSignature SAP + AMD/Anisette） | 见 protocol skill |

> 🔴 关键：注册页强制 L3/L4 → **L1 hook 救不了模拟器**（服务端要 Google 签名的真 token）。L4 不可伪造时，模拟器注册止损。

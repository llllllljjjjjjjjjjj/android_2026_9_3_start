# SO 代码段脱密（运行期解密壳：梆梆 / 爱加密 native）

> 本文件由 `SKILL.md §4 SO 代码段脱密` 引用，属于**按需加载**层：native .text 磁盘加密、运行期解密到内存的壳，需要 dump 解密段并回填 IDA 时读。

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

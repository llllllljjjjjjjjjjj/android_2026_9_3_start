# 壳识别目录 + 加固成功率 + 实战案例（查表手册）

> 本文件由 `SKILL.md 阶段 1（壳识别）`、`§5 实战案例`、`加固成功率参考` 引用，属于**按需加载**的查表/案例层：识别壳厂商特征 so/包名、评估各加固脱壳成功率、复用已验证案例时读。

---

# 阶段 1：壳厂商特征对照表

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

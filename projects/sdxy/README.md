# sdxy — 闪动校园

## 目标

逆向 `sdxy.apk`（闪动校园 App v8.6.8），脱壳 + 提取 API + 还原协议签名算法。

## 关键信息

| 项 | 值 |
|----|-----|
| 包名 | `com.huachenjie.shandong_school` |
| 应用名 | 闪动校园 |
| 版本 | 8.6.8（version_code 26082615） |
| 原始 APK | `apk/sdxy.apk`（293,546,757 字节） |
| 框架 | Flutter（`libapp.so`）+ Kotlin/Java 模块 |
| 加固 | 网易易盾 NIS `7.6.3_936`（`com.netease.nis.wrapper`） |
| 壳 SO | `libNetHTProtect.so` + `libnesec.so` |
| BaseUrl | `https://api.huachenjie.com/` |
| 加密 | AES-256-CBC + SHA256 sign（详见 docs/REVERSE_REPORT.md） |

## 现状

- ✅ 脱壳完成：内存扫描 dump 12 个业务 dex，jadx 合并反编译 22149 类（5111 业务类），方法体完整
- ✅ API 端点全部提取（`run-front/*`，375 个 API 文件）
- ✅ 加密/签名算法完整还原（AES-256-CBC + IV 固定 + SHA256 旋转 + Base64）
- ⚠️ 密钥值未提取：native 懒初始化 + 设备无网 + 易盾反 Frida（止损点，见报告 §4）

## 目录

- `apk/` — 原始 APK、vdex、dump 的 76 个 dex
- `decompiled/` — 壳代码（易盾 wrapper）
- `decompiled_biz/` — 业务 dex 反编译产物（`all/` 为 12 个业务 dex 合并）
- `so_analysis/` — 关键 SO
- `hooks/` — Frida 脚本（脱壳/枚举/密钥）
- `scripts/` — Python 脚本（扫描/dump/分类/RPC）
- `docs/REVERSE_REPORT.md` — 完整逆向报告
- `artifacts/` — 日志与中间产物

## 入口

- 主 Activity：`com.huachenjie.shandong_school.splash.SplashActivity`
- 业务 Application：`com.huachenjie.shandong_school.ShandongApplication`（方法被易盾 native 化）
- 加密拦截器：`huachenjie.sdk.http.security.core.EncryptInterceptor`
- 签名拦截器：`huachenjie.sdk.http.interceptor.ParamsInterceptor`
- 业务模块：`com.huachenjie.{sport,running,social_contact,mall,works,channel,college,login,mine,home,im,common,base}`

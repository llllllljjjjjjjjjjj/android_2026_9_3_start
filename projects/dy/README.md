# dy — 抖音（Douyin）逆向项目

> **当前任务**：逆向视频评论接口（评论列表 / 详情相关 API），输出接口、参数、签名/鉴权要求与调用链。

## 样本

- `apk/dy.apk`（250,726,329 B，原始样本同 `projects/apk/dy.apk`）
- 形态：50 个 `classes*.dex` 平铺根目录，无商业加固壳特征 so → 字节系原生多 dex 分包，jadx 可直接反编译
- 网络栈：`libttboringssl.so` / `libsscronet.so`（TTNet/sscronet，Chromium 系）

## 目录

```
apk/         原始 APK
decompiled/  jadx 反编译产物（reverse_index 索引对象）
artifacts/   解出的 dex 等中间产物
hooks/       项目专属 Frida 脚本
scripts/     项目专属 Python
capture/     抓包 flows
so_analysis/ native so 分析
docs/        接口文档 / 分析笔记
```

## 现状

- 2026-08-18：反编译进行中。

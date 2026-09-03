# projects/ — 逆向项目库

> **可以直接复制**：本项目库不参与任何转换，整目录随便携包走。换电脑/换环境时
> 把 `projects/` 原样复制即可（或运行根目录 `pack.ps1` 一键打包）。

## 目录规范

每个目标一个目录，结构固定（技能与 MCP 均按此约定工作）：

```
projects/<target>/
├── apk/          ← 原始 APK 与脱壳产物
├── decompiled/   ← jadx/apktool 反编译源码（reverse_index 索引对象）
├── hooks/        ← Frida/脚本
├── scripts/      ← 项目专属 python/powershell
├── so_analysis/  ← native so 分析（含 vcn/lib 等）
├── capture/      ← 抓包数据（parsed/ 为解析产物）
├── artifacts/    ← dex/so 等提取产物
├── docs/         ← 笔记、方案（risk-control-adversary 唯一允许写入处）
└── README.md     ← 项目说明
```

## 当前项目

| 项目 | 说明 | 关键产物 |
|------|------|----------|
| `dy/` | 抖音（Douyin）逆向：dex 57 个、decompiled 源码、so_analysis（libttcrypto/libsscronet/libmetasec_ml/vcn 三件套）、hook_req（kitsunebi 配置） | `artifacts/dex/`、`so_analysis/` |
| `dcgc/` | 另一目标：apk/capture/hooks/scripts/so_analysis | — |
| `apk/` | APK 样本仓库 | — |

## 复制/打包

```powershell
# 一键打包整个便携工作台（含 projects/）到目标目录
& .\pack.ps1 -Destination D:\work\reverse-kit

# 只复制项目库
robocopy projects D:\work\reverse-kit\projects /E /XD __pycache__ /NFL /NDL /NJH /NJS
```

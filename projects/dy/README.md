# dy — 抖音 (com.ss.android.ugc.aweme)

## 目标说明
- 版本: **38.0.0 (380001)**
- 原始 APK 归档: `apk/dy.apk`（345,543,863 B）
- SHA256: `A1BE844DC4F60DCBF2C2DB205E3189D308CC804C93ED0A15B522FB9F31EF6365`
- 包名: `com.ss.android.ugc.aweme`（抖音主端）
- 设备基线: Pixel 4 (flame) `9C181EC3BF7E0D` · Android 10 / SDK 29 / arm64-v8a · Magisk

## 现状（全部完成）
- [x] 目录骨架
- [x] 壳检查（无商业加固，native 仅 libmetasec_ml.so 签名库）
- [x] jadx 反编译 → `decompiled/sources/`（**504,699 个 .java**）
- [x] reverse_index 索引 → `artifacts/reverse_index.sqlite`（4.1 GB）
- [x] 网络栈识别（TTNet / libsscronet / libttboringssl）
- [x] 签名体系分析（ClientKey 可用 RPC；八神不在搜索链路）
- [x] **搜索接口打通**（按关键词取真实结果 + 视频下载）

## 交付能力（绕过型）

| 能力 | 工具 | 输出 |
|---|---|---|
| 关键词搜索 | `scripts/search_pull.py <kw> [pages] [delay]` | `capture/results_<kw>.json` |
| 视频详情 | `scripts/detail_pull.py <aid>` | `capture/detail_playcount.json` |
| **视频 + 下载** | `scripts/video_pull.py --download <aid>` | `capture/videos/<aid>.mp4` |
| 用户主页 | `scripts/user_pull.py <uid>` | `capture/users.json` |
| 签名 oracle | `scripts/sign_rpc.py ckheaders` | ClientKey 头 |

## 入口
- **使用文档**: `docs/USAGE.md` ← 先看这个
- **接口谱系**: `docs/api-map.md`
- 打通全过程: `docs/search-poc.md`
- 签名 oracle: `docs/sign-oracle.md`
- 参数谱系: `docs/parameter-lineage.md`
- 反编译产物: `decompiled/`　Hook: `hooks/`　数据: `capture/`
- 笔记: `docs/recon.md`、`docs/static-overview.md`、`docs/search-flow-analysis.md`、`docs/risk-observations.md`

## 关键结论（实证）
1. 搜索主接口 `POST /aweme/v2/search/general/stream/`（form，90 参数），走 TTNet → HTTP/2 + Brotli → Gson 解析
2. **离线重放不可行**：签名层通（服务端接受），业务层空 —— 公共参数在 native 层
3. **RPC 桥接可行**：hook `SearchMixFeed.getAweme()` 是稳定采集点
4. 播放量（`playCount`/`play_count`）**服务端不返回**（两接口皆 0）
5. 八神签名（x-argus/gorgon）**不在搜索链路**

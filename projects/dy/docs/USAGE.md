# dy 数据采集工具 — 使用文档

> 交付定位：**绕过型**（依赖真机 + App 运行态 + Frida RPC，**不称纯算**）
> 目标：抖音 38.0.0（`com.ss.android.ugc.aweme`，380001）搜索链路数据采集

## 1. 前置条件

| 项 | 值 |
|---|---|
| 设备 | Pixel 4 (flame) · serial `9C181EC3BF7E0D` · Android 10 / SDK 29 / arm64-v8a |
| Root | Magisk + Zygisk |
| frida-server | 魔改 `florida-server 16.5.9`（设备上运行） |
| Python venv | `.venv-frida-16.5.7`（frida 16.5.7） |
| ADB | `android_mcp\toolchain\bin\windows\platform-tools\adb.exe`（自带） |
| 端口转发 | `adb forward tcp:27042 tcp:27042` |

**每次开工前检查**：
```powershell
$ADB="android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
& $ADB devices                                  # 设备在线
& $ADB shell pidof com.ss.android.ugc.aweme     # App 运行中（没有则先启动）
& $ADB shell pidof florida-server               # frida-server 在跑
& $ADB forward tcp:27042 tcp:27042              # forward 建立
```

> 环境变量 `PYTHONIOENCODING=utf-8` 建议设置（避免 Windows 控制台编码问题）。

## 2. 四个工具

### 2.1 搜索：`search_pull.py`

```powershell
.venv-frida-16.5.7\Scripts\python.exe projects\dy\scripts\search_pull.py <关键词> [页数] [间隔秒]
```

| 参数 | 默认 | 说明 |
|---|---|---|
| 关键词 | `compass` | **支持中文**（内部自动 URL 编码） |
| 页数 | 1 | 1–10，每页 `input swipe` 滑动加载更多 |
| 间隔秒 | 4.0 | 翻页间隔（拟真节奏，防频控） |

**输出**：`capture/results_<关键词>.json` — 每条约 68 条/页

**示例**：
```powershell
search_pull.py 咖啡 3 5      # 咖啡，3 页，间隔 5s → 约 133 条
search_pull.py kayak         # 单页
```

### 2.2 视频详情：`detail_pull.py`

```powershell
detail_pull.py <aid> [more_aids...]
detail_pull.py --from results_滑雪.json 3      # 取搜索结果前 3 条 aid
```

**输出**：`capture/detail_playcount.json`

> 结论：**详情接口的 `play_count` 恒为 0** —— 抖音 API 层不提供播放量。

### 2.3 视频/图文（元数据 + 地址 + 文件）：`video_pull.py`

```powershell
video_pull.py <aid>                    # 元数据 + 播放地址/图片地址
video_pull.py --from results_hiking.json 5
video_pull.py --download <aid>...      # 视频→mp4，图文→多张图片
```

**输出**：`capture/videos.json`；文件落在 `capture/videos/`

**自动识别媒体类型**（`mediaType` 字段）：
| 类型 | 判据 | 下载产物 |
|---|---|---|
| `video` | 有 `play_addr.url_list` | `<aid>.mp4` |
| `album`（图文） | `images` 数组内有图片 URL | `<aid>_imgNN.<ext>` |
| `unknown` | 两者都无 | 记录不下载（不再静默丢弃） |

**要点与容错**
- **图文（awemeType=68）必须支持**：抖音搜索/详情结果里图文占相当比例（实测 582 条中 100 条）
- 图文的图片字段是 **`download_url_list`**（不是 `url_list`），且优先取 **webp** 变体
- 图片 URL 带 `x-expires`/`x-signature` **时效签名** → 获取后立即下载
- **扩展名按 magic 嗅探**（`sniff_ext`）而非写死：抖音原图可能是 **HEIF/VVC**（`ftyp` brand=`vvic`），
  写死 `.jpg` 会得到名不副实的文件
- 视频 URL 优选 `douyinvod.com` 并**排除** `douyinstatic.com`（图文背景音常落该域名）
- 单条目失败只告警不中断（`downloaded files: N, unexpected errors: 0`）

**实测（图文 `7665610765634568613`）**
```
img01.jpg  237,774 B  → JPEG SOI+EOI 完整, JFIF, 1024x1535  ✅
```
**实测（视频 `7657917544935046470`）**
```
7657917544935046470.mp4  3,442,252 B  → ftypisom + moov  ✅
```

### 2.4 评论：`comment_pull.py`

```powershell
comment_pull.py <aid> [滚动次数]              # 默认滚 3 次
comment_pull.py --from results_太阳.json 3    # 批量取前 3 条
```

**输出**：`capture/comments_<aid>.json`（`{aid, rawTexts, comments[]}`）

**⚠️ 命令提醒**：**评论少的视频没有翻页**，验证翻页务必换评论多的视频（实测用 97,375 条评论的
`7581630849533316401`，8 次滚动持续增长 9→16→23→27→33→39→47→55 texts）。

**实现（三层踩坑后的最终方案）**

| 层 | 结果 |
|---|---|
| 接口定位 | `POST /aweme/v2/comment/list/stream/?aweme_id=<aid>&cursor=0&count=20` — **流式接口** |
| chunk 消费端 | `ChunkDataStream<CommentItemList>`，chunk 类型 `CommentItemList` ✅ 能拿到 |
| `CommentItemList.items` | ❌ **为空**（`total` 能读到，如 `total=4`）；评论经 **`serverCommentData` 加密下发** |
| frida 读 List/字段 | ❌ 直读字段 `absent`、`getItems()` `not a function`、`toArray()` 也失败（包装限制） |
| Gson 序列化 | ⚠️ `toJson(CommentItemList)` 可拿到元数据，但 items 仍空 |
| **✅ 最终方案** | **UI 渲染层捕获**：`TextView.setText(CharSequence)` + **capture 时间窗**（仅评论区打开后记录） |

**字段与局限**

| 可获取 | 不可获取 |
|---|---|
| 昵称 / 评论文本 / IP 属地 / 回复数 / 点赞数 | **cid**（评论 ID）、sec_uid（需网络层） |

- 结构化准确率 **~80%**：文本流顺序为 `昵称 → [标签] → [· 属地] → 内容 → [展开N条回复]`，
  已在 `structure()` 中按此规则分组，并用 `LABELS` 过滤"作者赞过/置顶"等噪音
- `capture` 窗口机制避免全局 `setText` 噪音（仅点开评论后开始记录）
- 止损：连续 2 次滚动无新增即停

### 2.5 用户主页：`user_pull.py`

```powershell
user_pull.py <uid> [more_uids...]
user_pull.py --from results_冲浪.json 3
```

**输出**：`capture/users.json`

> 当前可得：`nickname`/`uid`/`secUid`/`uniqueId`/`signature`/**`follower`**；`awemeCount`/`totalFavorited` 仍空。

## 3. 脚本 ↔ hook 对应关系

| Python 工具 | Frida 脚本 | hook 点 |
|---|---|---|
| `search_pull.py` | `hooks/hook_searchcard_rpc.js` | `SearchMixFeed.getAweme()`（搜索卡渲染必调） |
| `detail_pull.py` | `hooks/hook_detail_rpc.js` | `Gson.fromJson` 过滤 `play_count` |
| `video_pull.py` | `hooks/hook_video_rpc.js` | `Gson.fromJson` 过滤 `play_addr` |
| `user_pull.py` | `hooks/hook_user_rpc.js` | `Gson.fromJson` 过滤 `follower_count` |

**共用机制**：
- **参数/签名/会话全部由 App 生成**（deeplink 触发真实搜索/打开视频）
- 数据经 **Frida RPC（JSON 通道）** 回传 —— 避免 stdout 编码破坏中文
- `hook_searchcard_rpc.js` 按 `aid` 去重

## 4. 故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| `unable to find process with name` | dy 反枚举（SF-016） | 脚本已用 `adb pidof` 直连；确认 pid 变化后重跑 |
| App 崩溃 / `Process terminated` | hook 了高频方法（如 `HashMap.put`/`getAid`）或传了多余参数 | 只用已验证的低频 hook 点；`o.apply(this, args)` 传实际参数 |
| 结果混入上次关键词内容 | 旧搜索卡在页面重渲染时被采集 | 已内置：触发前 `input keyevent 3`（HOME）清场 |
| 中文乱码 | stdout 编码链路 | 已内置：RPC 回传 + UTF-8 落盘 |
| `Script.exports will become asynchronous` | frida 旧 API | 已改用 `exports_sync` |
| 翻页无新增 | 滑动未触发加载 / 频控 | 增大间隔（第 3 参数），或确认 App 前台 |

**纪律**：同接口同错误**连续 3 次**即停止，保存证据并归因（AGENTS.md 验证期纪律）。

## 5. 依赖与边界（止损型必须明示）

**依赖**：真机 + App 运行态 + florida-server + Frida RPC + `adb forward`。
**边界**：
- App 重启后 pid 变化，需重新 attach
- deeplink 可直达：搜索页 / 视频详情 / 用户主页
- **deeplink 无法直达评论区** → 评论、直播未实现（需 UI 操作，超出「无 UI 优先」范围）
- 长期高频 RPC 有被检测风险

**禁止事项**（踩坑沉淀）：
- ❌ hook 高频集合方法（`HashMap.put`）并在其中构造对象 → App SIGSEGV
- ❌ hook 极高频率 getter（`Aweme.getAid`）→ 性能崩溃
- ❌ 传多余 `undefined` 参数给 frida overload wrapper → `toJni` 错误崩溃
- ❌ 用 PowerShell `Tee-Object` 存数据再用 UTF-8 读 → 实为 UTF-16LE

## 6. 相关文档

| 文档 | 内容 |
|---|---|
| `docs/api-map.md` | **接口谱系**（接口清单 / host 调度 / 数据流 / 字段来源） |
| `docs/search-poc.md` | 打通全过程记录（10 节 + 全部实证与踩坑） |
| `docs/sign-oracle.md` | 签名 RPC oracle（ClientKey 可用 / 八神不在搜索链路） |
| `docs/parameter-lineage.md` | 参数谱系（客户端生成 vs 服务端下发实证） |

# dy 搜索接口打通（A 方案：RPC 桥接交付）

生成：2026-09-07 ｜ 形态：**绕过型/止损型**（依赖真机 + App 运行态 + Frida RPC，非离线纯算）

## 1. 方案架构

```
Python (resp_rpc.py)
   ├─ adb deeplink 触发: snssdk1128://search?keyword=X   ← 由 App 自己发起搜索
   └─ Frida RPC (resp_oracle.js) ← App 解析到的响应缓存
                    ↑
              hook JSONTokenerGetter.get(String)   ← 参数/签名/会话全由 App 生成(native 层不可见的部分也齐全)
```
**核心价值**：参数生成完全交给 App（含 TTNet native 层追加的参数），我们只负责触发与读取 —— 这是"参数生成用 RPC"的落地形态。

## 2. 已实测拿到（真实业务数据）

| 数据 | 响应大小 | 证据 |
|---|---|---|
| **搜索卡片数据**（词典/百科卡） | 33,878 B | 顶层 `ala_src/display/doc_id/query/synthesis_text/search_enter_from/strong_corrected_query` |
| **搜索会话日志**（含 search_id） | 15,934 / 15,708 B | `trigger/itemCount/netLogId/status/is_first_search` + `search_id=202609101957051898565A1F91B1AF9F52` |
| **埋点上报包**（加密） | 146,486 B | `magic_tag/time_sync/header/key/iv/event_v3`（`key`/`iv` → 埋点数据 AES 加密） |
| 搜索历史/特征接口响应 | 197–5,352 B | 多份 |
| 落盘响应总数 | 60 份 | `capture/resp_pottery_*.json` |

## 3. 未拿到 / 未通（诚实标注）

| 缺口 | 原因（推测，待证） |
|---|---|
| **视频结果列表**（aweme_list + desc） | 扫描 60 份响应无 `aweme_id`+`desc` 组合 → 搜索结果疑走**流式 chunk**（`general/stream`），不经 `JSONTokenerGetter`；需 hook `ChunkDataStream`（`com.bytedance.android.chunkstreamprediction.network.ChunkDataStream`） |
| **离线自主发请求**（不用 App） | 已到签名层：服务端接受请求（`status_code:0`）但返回**空壳** `{"has_more":0,"cursor":10,"category_list":[]}`；body 90 参数无 device_id/aid → 公共参数主要由 TTNet native 层追加（另注：`url_samples.txt` 显示部分搜索接口 URL **确实带 query**，如 `vtag/?klink_egdi=...&iid=3050145571` 含 `iid`，故"URL 无 query"仅对 `general/stream` 成立） |

## 4. 与离线重放的分层结论

| 层 | 状态 | 关键证据 |
|---|---|---|
| 网络可达 | ✅ | HTTP 200 |
| **签名层** | ✅ | 服务端返回业务响应（非风控拒绝）→ `X-Tt-Token` + `x-bd-client-key` 有效 |
| 业务层（离线重放） | ❌ | 空壳响应 → 缺 native 层追加参数 |
| 业务层（RPC 桥接） | ⚠️ 部分 | 拿到卡片/会话/埋点数据；视频列表待补 |

## 5. 交付物

| 文件 | 作用 |
|---|---|
| `hooks/resp_oracle.js` | Frida：响应缓存 + RPC（count/list/get/getlatest/find/clear） |
| `scripts/resp_rpc.py` | 调用器：`search <kw>` 触发并落盘响应 |
| `hooks/sign_oracle.js` + `scripts/sign_rpc.py` | 签名 oracle（`clientkeyheaders` 可用） |
| `capture/resp_pottery_*.json` | 60 份真实响应 |
| `scripts/poc_search.py` | 离线重放 POC（签名层通，业务层空） |
| `scripts/verify_responses.py` / `extract_search_sample.py` | 响应校验与样例提取 |

## 6. 视频列表攻坚（本轮，未通，含实证）

| 尝试的 hook 点 | 结果 | 结论 |
|---|---|---|
| `SearchMixFeedList.setJsonData()` / `getItems()` | **0 次命中** | 该模型是 **v1** 接口（`/aweme/v1/general/search/stream/`）；实际搜索走 **v2**（`/aweme/v2/search/general/stream/`），不用此模型 |
| `ChunkDataStream.subscribe` | 未命中 | 通用流式容器，非搜索专用入口 |
| `libttboringssl` SSL_read 抓包（阻断 UDP 前后各一次） | 抓到 664KB / 710KB，**无任何搜索 JSON**（`aweme`/`search`/`gzip` 全 0 命中）；首字节 `00 00 08 06 01` = **HTTP/2 SETTINGS 帧** | 搜索主响应**不经该 TLS 实例**（疑 QUIC 或另一份 BoringSSL 副本） |

**静态定位结论**
- 搜索主接口有两个：**v1** `POST /aweme/v1/general/search/stream/` → `ChunkDataStream<SearchMixFeedList>`（模型含 `List<SearchMixFeed> f` + `getItems()`）；**v2** `POST /aweme/v2/search/general/stream/`（实际使用）
- v2 入口在 `com.ss.ugc.android.ugc.aweme.search.general.SearchGeneralPageModuleRegistry`（NetworkConfig: v2 single/stream），该包仅 2 个文件、**无响应模型** → 模型在其他包或 X 混淆桶
- v2 请求头含 `x-nx-chunk`、`Use-Stream`、`Accept`（流式分块协议）

**下一步（未做）**
1. 定位 v2 搜索的响应模型 / chunk 解码器（从 `SearchGeneralPageModuleRegistry` 反向追）
2. 或 hook `ChunkDataStream` 内部 chunk HashMap 的填充
3. 或枚举抖音进程内**所有** BoringSSL 实例（`SSL_read` 多副本），排除漏抓

## 6.5 视频列表攻坚（第二轮：协议层实证，仍未拿到列表）

| 尝试 | 结果 | 结论 |
|---|---|---|
| `ChunkDataStream.subscribe` **代理 hook**（`Java.registerClass` 实现 `ChunkDataObserver`） | ✅ 生效：捕获 6 chunk + complete | chunk 类型 `X.0XPQ`，`toString` 仅返回对象地址（无内容）→ **搜索视频列表不走此流** |
| HTTP/2 帧解析（自写解析器） | ✅ 157 帧（DATA 94 / HEADERS 36 / PING 14 / SETTINGS 4 …） | 抓包流确为 HTTP/2 |
| **Brotli 解压**（`brotli` 库） | ✅ **解压成功**（`{"extra":{...,"logid":...}}`、`{"server_time":...,"address_list":[]}`） | **实证响应走 Brotli 压缩** —— 对应配置 `"ttnet_enable_br": 1` |
| 搜索数据提取 | ❌ 94 个 DATA 帧仅 2 个解压成功且非搜索数据 | `resp_stream.bin` 为**多连接 SSL_read 顺序拼接、未按连接重组** → 帧边界错乱，需按连接/流重组 |

## 6.6 本轮新增关键实证（协议配置层）

| 发现 | 证据 |
|---|---|
| **TTNet 启用 Brotli** | `CronetDepeendAdapter` 配置 `"ttnet_enable_br": 1` + `ttnet_h2_enabled: 1` + 实测 br 解压成功 |
| **搜索 host 被调度替换** | 同配置 `act_priority 1002, description:"search"` → 搜索接口 host 替换为 **`search3-search.amemv.com`**；feed→`api3-core-c.amemv.com`；普通→`api3-normal-c.amemv.com` |
| 长连接/推送走专线 | `frontier_urls: wss://frontier-aweme.snssdk.com/ws/v2`；`/webcast/*`、`/ws` → dispatch 策略 priority 199 |
| 搜索接口 v1/v2 并存 | v1 `/aweme/v1/general/search/stream/`（`SearchApi$RealApi` 3 处定义）→ `ChunkDataStream<SearchMixFeedList>`；v2 `/aweme/v2/search/general/stream/`（实际使用）在 `search/general` 包 |
| **host 修正后重放仍空** | 改用 `search3-search.amemv.com` 重放 → 同样返回 `{"has_more":0,"status_code":0,"cursor":10,"category_list":[]}` → **host 不是空数据原因**；真正缺的是 native 层参数/新鲜会话（已按纪律停止第 3 次重试） |

## 8. ★ 打通成功（2026-09-07，A 方案 RPC 桥接）

**结论：搜索接口已按关键词成功拉取真实搜索结果。**

```
python projects\dy\scripts\search_pull.py <keyword>
   ↓ deeplink 触发 App 搜索（参数/签名/会话全由 App 生成）
   ↓ Frida hook SearchMixFeed.getAweme()（搜索结果卡模型，UI 渲染必调）
   ↓ RPC 回传（JSON 通道，UTF-8 无损）
   → capture/results_<keyword>.json
```

**实测结果（keyword=kayak，10 条）**

| aid | desc | digg |
|---|---|---|
| 7158074377907506467 | 亮哥带你刷考研词汇 字形法no.101 compass #考研词汇 #考研英语 | 169 |
| 7657917544935046470 | 硬艇最基础的乐趣-爱斯基摩翻滚我又体验到了… | 26 |
| 7226571276373019960 | Kk for kayak，kayak啥意思？ #启蒙英语 #零基础英语 | 92 |
| 7663033602246916745 | 钓鱼不用很大的船，小小kayak卡亚克也可以玩的很开心 | 209 |
| 7665610765634568613 | 六类常见船只：boat/ship/vessel… | 3077 |

**关键突破点 = `SearchMixFeed.getAweme()`**
- 该 hook 点此前 3 个候选（`SearchMixFeedList` / `ChunkDataStream` / `JSONTokenerGetter`）全部落空
- 定位路径：`SearchMixFeed` 源码含 **Gson 注解**（`@SerializedName`/`@JsonAdapter`）→ 排除 org.json 路径 → 转向卡模型自身的 getter
- `SearchMixFeed.getAweme()` 在**搜索结果卡渲染时必被调用** → 稳定拿到 `Aweme`（aid/desc/author/statistics）

**交付形态（三级交付定位）**：**绕过型**
- 明示条件：依赖真机 Pixel4 + App 运行态 + florida-server + Frida RPC；**不称纯算**
- 未解字段：`createTime`/`comment`/`share`/`play`/`duration` 取空（getter 名或调用时机不同，可继续补）
- 优势：参数（签名/公共参数/会话）全部由 App 侧生成，**不受 native 层不可见参数限制**

**交付物**
| 文件 | 作用 |
|---|---|
| `hooks/hook_searchcard_rpc.js` | Frida：hook `SearchMixFeed.getAweme()` + RPC 回传卡片（去重） |
| `scripts/search_pull.py` | 一键：`python search_pull.py <keyword>` → 落盘 UTF-8 JSON |
| `capture/results_kayak.json` | 实测结果样本 |

**字段谱系（全部打通，实测 keyword=hiking / bicycle）**

| 字段 | 来源 | 取值方式（实证） | 状态 |
|---|---|---|---|
| `aid` | 服务端 | `Aweme.getAid()` | ✅ |
| `desc` | 服务端 | `Aweme.getDesc()` | ✅ 中文无损 |
| `createTime` | 服务端 | 字段 `createTime` | ✅ |
| `duration` | 服务端 | **字段 `videoLength`**（非 `duration`，见 `Video.java:431`） | ✅ 毫秒 |
| `digg`/`comment`/`share`/`collect` | 服务端 | `AwemeStatistics` **public 字段** `diggCount`/`commentCount`/`shareCount`/`collectCount` | ✅ |
| `play` | 服务端 | `playCount` 字段存在但值为 0（接口不返回播放数） | ⚪ 空 |
| `author`/`uid` | 服务端 | `getAuthor()` → 字段 `nickname`/`uid` | ✅ |
| `awemeType`/`textExtra` | 服务端 | getter / 字段 | ✅ |

**关键踩坑（字段取值）**
- `AwemeStatistics` 的计数是 **public 字段 + @SerializedName**，**没有 getter** → 必须字段直读（`st.diggCount.value`）
- `Video` 的时长字段是 **`videoLength`**（`@SerializedName("duration")` 映射到它），不存在 `duration` 字段

**实测样本（keyword=hiking，14 条）**
```json
{"aid":"7508320729704992060","createTime":"1748167152","digg":"16060",
 "comment":"357","share":"0","collect":"1803","play":"0","duration":"19553"}
```

**使用说明与已知问题修复（2026-09-07 实跑反馈）**

```powershell
.venv-frida-16.5.7\Scripts\python.exe projects\dy\scripts\search_pull.py <keyword>   # 支持中文
```

| 问题 | 现象 | 修复 |
|---|---|---|
| **中文关键词崩** | `UnicodeDecodeError: 'gbk' codec can't decode byte 0xaa` | `subprocess.run(..., encoding="utf-8", errors="ignore")`（adb 输出固定 UTF-8 解码） |
| **中文关键词不触发搜索** | 结果混入上一次关键词（跑「太阳」第 1 条仍是 hiking） | 关键词 **URL 编码**：`urllib.parse.quote(kw)` → `snssdk1128://search?keyword=%E5%A4%AA%E9%98%B3` |
| **旧卡片残留** | 「咖啡」结果第 1 条是上次的太阳 | 触发前先 `input keyevent 3`（HOME）清掉上一次搜索页 |
| frida 弃用警告 | `Script.exports will become asynchronous` | 改用 `script.exports_sync` |

**验证**：`太阳` → 8 条全为太阳相关；`咖啡` → 68 条全为咖啡相关（含滚动加载多页），首条即 `复刻这杯经典"西西里冰手冲"`。

**翻页（A）与统计字段完整实证（C）**

```powershell
# 翻页：第二个参数 = 页数（每页 adb swipe 加载更多），最多 10
.venv-frida-16.5.7\Scripts\python.exe projects\dy\scripts\search_pull.py 咖啡 3
```

**翻页实测**：`咖啡` 3 页 → **133 条**（单页约 68 条）；每页滑动 `input swipe 540 1800 540 620 400`，间隔 4s（拟真节奏，避免风控）。

**统计字段非零率（133 条样本，实证）**

| 字段 | 非零数 | 结论 |
|---|---|---|
| `aid`/`desc`/`createTime`/`duration` | 133 | ✅ 全量返回 |
| `digg` / `collect` / `comment` / `share` | 132 / 129 / 127 / 123 | ✅ |
| `recommendCount` | 108 | ✅ 新补 |
| `downloadCount` | 47 | ✅ 新补 |
| `forwardCount` | 2 | ✅ 新补 |
| **`playCount`** | **0** | ⚪ **服务端不返回**（字段存在于 `AwemeStatistics:76-77` `@SerializedName("play_count")`，恒为 0） |
| **`exposureCount`** | **0** | ⚪ 服务端不返回 |

> 结论：抖音**搜索结果接口不提供播放量/曝光量**——需播放数须转视频详情接口（如 `/aweme/v1/multi/aweme/detail/`），非本接口字段缺失。

## 9. 扩展交付（①②③ + 收尾）

### ③ 速率控制与容错（完成）
`search_pull.py <keyword> [pages] [delay]`
- `pages` 1–10（每页 `input swipe` 加载更多）
- `delay` 翻页间隔秒（默认 4s，拟真节奏防频控）
- `adb_retry()`：3 次尝试 + **线性退避**（2s/4s）
- `attach_script()`：连接失败退避重试（3 次）
- `try/finally` 保证 detach；`sys.exit(main())` 返回真实退出码

**实测**：`滑雪 2 5` → 136 条（delay=5s）。

### ① 视频详情 playCount（完成 — 结论：**抖音 API 不提供播放量**）
`detail_pull.py <aid>...` 或 `--from <results_x.json> [n]`

| 接口层 | 字段 | 实测值 |
|---|---|---|
| 搜索结果 | `statistics.playCount` | **0**（字段存在，恒为 0） |
| 视频详情 | `play_count`（Gson 详情响应） | **0** |

**实证结论**：`AwemeStatistics:76-77` 确有 `playCount` 字段，但**搜索接口与详情接口都不下发该值** → 播放量在抖音 API 层不可得（产品决策，非技术限制）。

**附带收获**：detail hook 用 Gson 过滤 `play_count` 的方式**能稳定抓到详情页原始响应**，是通用「详情接口采集」入口。

### ② 更多接口
| 接口 | 状态 | 说明 |
|---|---|---|
| **用户主页** | ⚠️ 部分 | `user_pull.py <uid>` / `--from results_x.json [n]`：拿到 `nickname`/`uid`/`secUid`/`uniqueId`/`signature`/**`follower`**（实测 kikyo 粉丝 12206）；`awemeCount`/`totalFavorited` 仍空（需继续定位） |
| **评论** | ❌ 未做 | deeplink 无法直达评论区，需 UI 操作 → 超出「无 UI 优先」范围 |
| **直播** | ❌ 未做 | 需 room_id 且模型复杂，同上 |

**② 关键细节**：粉丝数出现在视频卡埋点的 **`mix_follower_count`** 嵌套串（`{"<uid>":21183}`），需二次正则提取。

### 附加修复：`author`/`uid`（重要）
原先 `author`/`uid` 全空，根因：**`Aweme.author` 与 `Aweme.statistics` 都是 public 字段，没有 getter**（`getAuthor()` 不存在）。
- 修复：`fieldObj(a, ["author"])` 字段访问 → **21/21 条**拿到 `author`/`uid`/`secUid`/`uniqueId`
- 实测：`冲浪` → `author=kikyo, uid=2997728419527804`

### ④ 交付清单（最终）
| 文件 | 作用 |
|---|---|
| `hooks/hook_searchcard_rpc.js` | 搜索结果卡 hook（全字段 + 去重 + RPC） |
| `hooks/hook_detail_rpc.js` | 视频详情 hook（Gson 过滤） |
| `hooks/hook_user_rpc.js` | 用户主页 hook（Gson 过滤 + mix 兜底） |
| `scripts/search_pull.py` | 搜索（关键词/页数/间隔 + 重试） |
| `scripts/detail_pull.py` | 视频详情批量 |
| `scripts/user_pull.py` | 用户主页批量 |
| `capture/results_*.json` `users.json` `detail_playcount.json` | 实测数据 |

## 10. 通过 aid 拿视频（元数据 + 播放地址 + 文件下载）

```powershell
# 元数据 + 播放地址
.venv-frida-16.5.7\Scripts\python.exe projects\dy\scripts\video_pull.py <aid>
# 批量（取自搜索结果）
.venv-frida-16.5.7\Scripts\python.exe projects\dy\scripts\video_pull.py --from results_滑雪.json 3
# 下载视频文件
.venv-frida-16.5.7\Scripts\python.exe projects\dy\scripts\video_pull.py --download <aid>
```

**实现**：`hook_video_rpc.js` hook Gson 解析，过滤含 `play_addr` 的详情响应，正则提取 `url_list` 数组。

**实测（aid=7657917544935046470）**

| 项 | 值 |
|---|---|
| desc | 硬艇最基础的乐趣-爱斯基摩翻滚我又体验到了… |
| duration | 23800 ms |
| 分辨率 | 720x720 |
| playUrl | `https://v26-cold.douyinvod.com/424ec4631b370f8a6914a465af5bd363/6aa2f55f/video/tos/cn/tos-cn-ve-15/...` |
| **下载文件** | `capture/videos/7657917544935046470.mp4` — **3,442,252 B** |
| 文件校验 | head=`ftypisom`，含 `ftyp`+`moov` box → **有效 MP4** ✅ |

**要点**
- CDN 每次返回**不同节点 URL**（v26-cold / v5-mc-cold），都可用
- 下载需带 **App UA + Referer**（`com.ss.android.ugc.aweme/380001 ...` / `https://www.douyin.com/`）
- URL 含时效签名（`.../6aa2f55f/...` 段），应在获取后**立即下载**
- 同时可提取 `cover`（封面）、`download_addr`（下载地址）、`bit_rate`/`gear_name`/`codec_type`（码率档位）

## 7. 踩坑（本轮新增，务必避免）

1. **hook `HashMap.put` 崩溃 App**：热路径 + 在其中构造 `JSONObject` → `JNI DETECTED ERROR: java_string == null` → SIGSEGV（还与 App 自身 `libbytehook.so` 冲突）。**禁止 hook 高频集合方法并在其中做重操作**。
2. **`Tee-Object` 写文件默认 UTF-16LE** → python 按 utf-8 读会全部乱码；需按 BOM 自适应解码。
3. **抖音 pid 会变**（App 自行重启）：frida CLI 硬编码 pid 必失败 → 每次 `adb pidof` 动态取（SF-016）。
4. **frida RPC 回调无 Java 上下文** → 返回 `Promise + Java.perform`。
5. **`Map.Entry.getKey/getValue` 不可用** → 绕道 `new JSONObject(map)`。

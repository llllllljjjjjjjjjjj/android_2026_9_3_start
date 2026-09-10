# dy 接口谱系（API Map）

> 全部条目均标注证据来源；未实证项标 `[未证]`。目标：抖音 38.0.0（380001）

## 1. 搜索链路接口（实测抓取）

| # | 接口 | 方法 | Host | 用途 | 证据 |
|---|---|---|---|---|---|
| 1 | `/aweme/v1/search/history_words_record/` | POST | `i.snssdk.com` | 搜索历史记录 | `capture/body_full.txt` REQ[1] |
| 2 | **`/aweme/v2/search/general/stream/`** | POST | `aweme.snssdk.com` → `search3-search.amemv.com` | **搜索主接口（流式）** | `body_full.txt` REQ[2] |
| 3 | `/aweme/v1/search/memory/upload_ei_feature/` | POST | `aweme.snssdk.com` | 搜索特征上报 | `body_full.txt` REQ[3] |
| 4 | `/2/wap/search/extra/tts/` | GET | `tsearch.toutiaoapi.com` | 词典/TTS 语音 | `body_full.txt` REQ[4] |
| 5 | `/aweme/v1/search/refresh_related_search/` | POST | `i.snssdk.com` | 相关搜索刷新 | `body_full.txt` REQ[5] |
| 6 | `/aweme/v1/search/multi_conversation/ai_guide_bar` | POST | `aweme.snssdk.com` | AI 引导栏 | `body_full.txt` REQ[6] |
| 7 | `/api/suggest_words/` | GET | `i.snssdk.com` | 搜索建议词 | 早期 dump |
| 8 | `/aweme/v1/search/vtag/` | GET | `tsearch.amemv.com` | 标签搜索（**URL 带 query**：`klink_egdi`/`iid`） | `capture/url_samples.txt` |
| 9 | `/aweme/v1/search/sign` | POST | `[未证]` | 轮询签名 | 静态 `PollingApi.poll` |

**主接口请求特征**（实测）
- `POST` + `application/x-www-form-urlencoded`，body **90 个参数**（`keyword`/`count`/`cursor`/`search_session_id`/`bcm_chain`/`template_extra_info`/`realtime_feature_channel`/`previous_search_ts`…）
- 流式协议头：`x-nx-chunk` / `Use-Stream` / `Accept`
- 响应：**HTTP/2 + Brotli**（`ttnet_enable_br:1`）

## 2. 其他链路接口

| 接口 | 用途 | 状态 |
|---|---|---|
| `/aweme/v1/multi/aweme/detail/` | 视频详情 | ✅ 可用（`video_pull.py`） |
| **`/aweme/v2/comment/list/stream/`** | **评论列表（流式）** | ⚠️ 部分（`comment_pull.py`，见下） |
| `/aweme/v1/comment/list/verify/` · `/aweme/v1/comment/list/reply/` | 评论校验 / 回复 | 未用 |
| 用户主页接口 | 用户资料 | ⚠️ 部分（`user_pull.py`） |
| 直播接口 | 直播 | ❌ 未做 |

**评论接口实测细节**
- 请求：`POST /aweme/v2/comment/list/stream/?aweme_id=<aid>&cursor=0&count=20&channel_id=-1&city=...`
  （body 含 `comment_common_user_data` / `comment_common_comment_data` 等客户端加密字段）
- 响应：**流式** → `ChunkDataStream<CommentItemList>`，chunk 类型 `com.ss.android.ugc.aweme.comment.model.CommentItemList`
- `CommentItemList` 可读字段：`total`（总数）、`cursor`、`hasMore`、`sessionId`（`<aid>:<uid>:<n>`）
- **`items`（List\<Comment\>）为空** → 评论文本经 **`serverCommentData`（加密）** 下发，
  且 frida 直读字段/`getItems()`/`toArray()` 均受限 → 最终改 **UI 渲染层捕获**（`TextView.setText` + capture 窗口）
- 可得：昵称 / 文本 / IP 属地 / 回复数 / 点赞数；不可得：`cid`、`sec_uid`

## 3. 静态定义但当前未走（v1 遗留）

| 接口 | 返回模型 | 实测 |
|---|---|---|
| `/aweme/v1/general/search/stream/` | `ChunkDataStream<SearchMixFeedList>` | **0 命中**（实际走 v2） |
| `/aweme/v1/general/search/single/` · `/aweme/v2/search/general/single/` | — | 未触发 |
| `/aweme/v1/search/item/` · `/aweme/v1/search/recommend/word/` | — | 未触发 |

## 4. Host 调度规则（实证，`CronetDepeendAdapter`）

| 优先级 | 业务 | 替换 Host |
|---|---|---|
| 1002 | **搜索**（`description:"search"`） | **`search3-search.amemv.com`** |
| 1000 | feed / aweme | `api3-core-c.amemv.com` |
| 1001 | 普通接口 | `api3-normal-c.amemv.com` |
| 101 | IM / 推送（dispatch） | `frontier-aweme.snssdk.com`（wss） |
| 102 | 强制 https | `*.snssdk.com` / `*.amemv.com` / `*.douyin.com` |

**其他协议开关**：`ttnet_h2_enabled:1`、`ttnet_enable_br:1`、`ttnet_http_dns_enabled:1`、`ttnet_url_dispatcher_enabled:1`

## 5. 数据流链（端到端）

```
deeplink snssdk1128://search?keyword=<kw>
   ↓
SearchGeneralPageModuleRegistry            (v2 搜索页模块, search/general 包)
   ↓
@POST /aweme/v2/search/general/stream/     (byte-retrofit, @FieldMap form)
   ↓
TTNet 层: 公共参数(native, Java 不可见) + 签名头 + host 调度 + Brotli
   ↓
HTTP/2 响应
   ↓
解析: Gson (@SerializedName / @JsonAdapter)   ← 非 org.json，故 JSONTokenerGetter 抓不到
   ↓
SearchMixFeed (搜索结果卡片基类, 字段含 Aweme aweme)
   ↓
★ SearchMixFeed.getAweme()  ← 渲染必调 = 稳定采集点
   ↓
Aweme { author(User) / statistics(AwemeStatistics) / video(Video) }
```

## 6. 字段谱系（完整，含取值方式）

| 字段 | 来源 | 取值方式 | 备注 |
|---|---|---|---|
| `aid` | 服务端 | `Aweme.getAid()` | 主键 |
| `desc` | 服务端 | **字段 `aweme.desc`** | 无 `getDesc()` |
| `createTime` | 服务端 | 字段 `createTime` | |
| `author`/`uid`/`secUid`/`uniqueId` | 服务端 | **字段 `aweme.author` → `nickname`/`uid`…** | 无 `getAuthor()` |
| `digg`/`comment`/`share`/`collect`/`recommend`/`download`/`forward` | 服务端 | **`AwemeStatistics` public 字段** | 无 getter |
| `play`/`exposure` | — | 字段存在 | **恒 0 → 服务端不返回** |
| `duration` | 服务端 | **`Video.videoLength`** | 非 `duration` |
| `awemeType` | 服务端 | getter | |
| `textExtra` | 服务端 | 字段 | 话题标签 |
| `playUrl`/`cover`/`downloadAddr` | 服务端 | 详情 `play_addr.url_list` | **含时效签名** |
| `imageUrl`/`imageCount` | 服务端 | 详情 `images[].download_url_list`（**优先 webp 变体**） | 图文（`aweme_type=68`）；原图可能是 HEIF/VVC（brand=`vvic`） |
| `mediaType` | 本地判定 | 有 images→`album`；有 play_addr→`video`；皆无→`unknown` | 实测 582 条中 type=68 有 100 条 |
| `follower` | 服务端 | `mix_follower_count` 嵌套串 / profile 响应 | |
| `search_id` | **服务端下发** | 响应字段 | 每次搜索签发（`YYYYMMDDHHMMSS`+22hex） |
| `session_id` | 会话级 | 响应回显 | 跨多次搜索复用 |

**服务端不提供**：播放量、曝光量（两接口皆 0）。

## 7. 签名与鉴权谱系

| 头 | 生成方 | 状态 |
|---|---|---|
| `X-Tt-Token` | `ClientKeyManager` | **跨请求逐字不变**（长期令牌）；结构 `[64hex]--[blob]-3.0.4` |
| `x-bd-client-key` | `getClientKeyHeaders()`（**RPC 可取**） | 128 hex；配置由**服务端下发**（`data.client_key_config`） |
| `x-bd-kmsv` | 同上 | `1` |
| `x-security-argus` | TTNet | 见 `capture/headermap.txt` |
| `activity_now_client` | TTNet | 时间戳 |
| **八神（`x-argus`/`x-gorgon`）** | `libmetasec_ml.so` | **不在搜索链路**（hook 实测 0 触发；库仅导出 `JNI_OnLoad`） |

## 8. 已知边界

1. **离线重放不可行**（业务层）：签名层通（服务端返回 `status_code:0`），但业务数据为空 —— 公共参数在 TTNet native 层（`general/stream`）
2. **host 修正不解决问题**：改用 `search3-search.amemv.com` 重放仍返回空壳 → 非 host 原因
3. **播放量不可得**：搜索 + 详情接口均返回 0
4. **评论/直播未做**：deeplink 不可直达，需 UI 操作
5. **A 方案（RPC 桥接）是唯一可行路径**：参数由 App 生成，我方只触发与读取

---

**证据文件**：`capture/body_full.txt`（90 参数）、`capture/headermap.txt`（签名头）、`capture/search_full_dump.txt`（6 接口）、`capture/url_samples.txt`（146 URL）、`capture/response_full.txt`（search_id）

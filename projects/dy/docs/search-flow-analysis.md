# dy 搜索接口整体流程 + 风控点 + 前置埋点上报链路

采集：静态（reverse_index 检索 + 关键类源码精读）+ 动态（libttboringssl 明文抓包实样）。
证据等级标注：已实证（源码行号/抓包实样）> 推测。

## 1. 搜索接口整体流程（分层调用链）

```
用户进入搜索框
  └─ SearchAdvanceNetRequestPresenter（discover/presenter/）
       前置预请求「猜词建议」SuggestWordsApi.getSuggestWordsWithRawString ("recom_search")
       ├─ 携带画像参数: history_search_query / feed_total_play_duration /
       │   enter_from(_second) / search_poi_info / aweme_life_channel /
       │   start_session / first_query_special_type / spu_id / poi_city / common_trans_info
       └─ 埋点: ISearchGuessTouchPrefetchHelper.sendGsTouchPrefetchMob("fail"/...)
                + SearchGuessOptPerformanceExp(性能埋点)

用户输入查词
  └─ SearchSugApi / SearchPredictApi（搜索建议/联想，防抖请求）

用户提交搜索
  └─ SearchApi（host 多路: search.amemv.com / i.snssdk.com /
       search.ecombdapi.com / tsearch.amemv.com）
      └─ SearchApi$RealApi：/aweme/v1/search/* 数十端点
         综合/用户/视频/音乐/商品/live/poi/hotlist/ai_summary/dynamic_tab/voice_sug ...

网络层
  └─ com.bytedance.retrofit2（字节魔改 Retrofit）→ TTNet（libsscronet + libttboringssl）
      └─ 拦截器注入签名头（见 §3）

搜索结果展示 / 点击
  └─ SearchResultShowEventTracker（discover/metrics/）
       show / click 埋点，MIN_CLICK_INTERVAL = 1000ms 节流

搜索实时通道
  └─ PollingApi：POST /aweme/v1/search/sign （search.realtime，轮询/签名）
```

## 2. 接口谱系（SearchApi$RealApi 实摘）

`/aweme/v1/search/` 前缀：ai_summary/answer_detail、multi_conversation/*、discuss/newest_comment、
dynamic_tab_v2、horizontal/loadmore、gpt/aisearch/*、pack、life_service_tab、page/loadmore、
feelgood_survey、memory/upload_ei_feature、voice_sug、experience、poi/vertical、load/inner_live、
search/sug、search/sign …（见 classes14.dex 反编译全文）

## 3. 风控点（六维识别，证据级）

### 3.1 签名校验（强，已实证）
- `X-Tt-Token`（ClientKey，kms_version 3.0.4）— 抓包实样 0051e8bf…3.0.4
- `bd-ticket-guard-key-sign`（TicketGuard 64hex）— 抓包实样
- `x-tt-token-supplement` / `x-bd-kmsv` / `x-tt-passport-mfa-token`（登录补充）
- 装配层: com.ss.android.token.TTTokenManager / account.PassportExtraHeaderManager / ttnet.clientkey.ClientKeyManager

### 3.2 参数完整性 = 行为画像载体（已实证，源码）
搜索请求体携带 `history_search_query`（历史搜索词）、`feed_total_play_duration`（浏览时长）、
`enter_from` 链路、`common_trans_info`（Nearby 注入）、`search_poi_info` —— **「只带必要参数」= 脚本指纹**，
全套参数本身就是画像/风控采集面。

### 3.3 设备指纹（bdturing 图灵风控，部分实证/部分推测）
- 头 `x-vc-bdturing-sdk-version`（抓包实样）
- com.bytedance.bdturing（BdTuringInterceptor / BdTuringInitProvider / ttnet interceptor）
- 采集面（环境/设备/行为特征）推测由 bdturing + argus SDK 完成

### 3.4 请求策略与行为画像（已实证，源码）
- `SearchResultShowEventTracker.MIN_CLICK_INTERVAL = 1000ms`：<1s 搜索结果点击被客户端直接拒
- `ComplianceServiceProvider.isGuestMode()`：游客模式拦截搜索请求
- sug 防抖、冷启动猜词缓存（SearchGuessSearchCacheManager）
- 行为序列（进入→预取→输入→提交→展示→点击）全链 mob/metrics 埋点

### 3.5 环境检测（推测，待真机验证）
- 反 Root/Frida/代理检测预期（字节通用）；本次抓包 hook 未触发秒退，未见实证阻断

### 3.6 业务规则（已实证，源码）
- entry 场景区分（homepage_hangout/life/mall/poi/fresh_video_detail → 不同 scene code 30122/9039x/90147）
- 游客态 / 登录态 / 生命周期场景（LifeMallConfig）分流

## 4. 前置埋点上报链路（重点）

风控不是「请求之后才上报」，而是**搜索意图产生的瞬间就开始打点**：

1. **进入态**：打开搜索框 = 预请求猜词（行为前置信令）+ `sendGsTouchPrefetchMob` 埋点 + 性能埋点
2. **请求体**：自带历史词/浏览时长/入口/POI 等画像字段（请求即采集）
3. **展示态**：SearchResultShowEventTracker 记录每次结果曝光（含 networkType、时间戳、sceneKey）
4. **点击态**：结果点击埋点，1000ms 最小间隔节流（防脚本点刷，也暴露真实用户节律）

## 5. 结论（对风控对抗的启示）
- 抖音搜索风控 = **强签名（ClientKey+TicketGuard）为入场门槛 + 全套行为画像参数 + 全链埋点节律**，
  属「强签名 → 先入场再谈行为拟真」场景（优先级 P0 = 签名/指纹）
- 单设备拟真须补齐：前置预请求（猜词）、画像参数历史链、1000ms+ 点击节律、埋点序列，缺一即异常
- 签名还原（ClientKey/TicketGuard 算法）→ 转 protocol-signature-reverser；环境对抗 → android-dynamic

证据文件：capture/dy_tls_plain.txt、capture/headers_sample.txt、decompiled .../discover/**、
decompiled .../search/**、reverse_index.sqlite（dy）

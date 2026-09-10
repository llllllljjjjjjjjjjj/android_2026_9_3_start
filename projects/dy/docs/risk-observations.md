# dy 风控观察记录

> 风控开关二 = YES（四核心技能动态条目）。E-cand/F-cand 候选，收割时由 risk-control-adversary 准入 L1/L3。

## 搜索接口风控点（2026-09-07，静态源码 + 抓包实样）

### [动态] E-cand 搜索点击节流（客户端 MIN_CLICK_INTERVAL）
- 类型: 请求策略与行为画像
- 检测原理: `SearchResultShowEventTracker.LJFF` 中 `j2 < 1000` 直接 return null，<1s 的搜索结果点击被客户端拒绝记录（源码 `discover/metrics/SearchResultShowEventTracker.java:159`）
- 对抗思路: 单设备搜索点击必须以 ≥1s 真实节律间隔，不可点刷
- 落地工具: 交叉引用 risk-control-adversary 单设备节奏（A3 §1）
- 证据等级: 已实证
- 置信度: 高
- 来源: projects/dy 2026-09-07 decompiled/.../discover/metrics/SearchResultShowEventTracker.java

### [动态] E-cand 搜索前置预请求画像（recom_search 猜词预取）
- 类型: 设备指纹+业务规则风控
- 检测原理: 进入搜索框即发 `SuggestWordsApi.getSuggestWordsWithRawString("recom_search")` 预请求，body 携带 history_search_query / feed_total_play_duration / enter_from(_second) / search_poi_info / common_trans_info 等画像字段（`discover/presenter/SearchAdvanceNetRequestPresenter.java`）
- 对抗思路: 搜索前必须补齐「进入→预取猜词→输入→提交」序列与画像参数，缺前置预请求或参数即异常
- 落地工具: 交叉引用 risk-control-adversary 单设备序列/参数完整性（A3 §2/§4）
- 证据等级: 已实证
- 置信度: 高
- 来源: projects/dy 2026-09-07 decompiled/.../discover/presenter/SearchAdvanceNetRequestPresenter.java

### [动态] E-cand 搜索签名头（ClientKey + TicketGuard）
- 类型: 签名校验（+设备指纹）
- 检测原理: 请求头 `X-Tt-Token`（ClientKey，kms_version 3.0.4）+ `bd-ticket-guard-key-sign`（TicketGuard）+ `x-tt-token-supplement` + `x-vc-bdturing-sdk-version`（bdturing 风控 SDK）；抓包实样见 capture/headers_sample.txt
- 对抗思路: 强签名=入场门槛（优先级 P0 签名），须先还原 ClientKey/TicketGuard 再谈行为
- 落地工具: 交叉引用 protocol-signature-reverser（签名还原）+ 静态定位 ttnet.clientkey / account.token
- 证据等级: 已实证
- 置信度: 高
- 来源: projects/dy 2026-09-07 capture/headers_sample.txt、decompiled ttnet/clientkey/ClientKeyManager.java

### [动态] E-cand 搜索实时签名轮询（search/sign）
- 类型: 签名校验
- 检测原理: `PollingApi.poll()` → `POST /aweme/v1/search/sign`（search.realtime），疑似搜索实时签名/预判通道
- 对抗思路: 需厘清该接口与搜索签名的依赖关系后才能稳定复现搜索请求
- 落地工具: 交叉引用 protocol-signature-reverser + android-recon 抓包补样本
- 证据等级: 小样本（仅接口定义，无线上报文）
- 置信度: 中
- 来源: projects/dy 2026-09-07 decompiled/.../discover/api/PollingApi.java

### [动态] E-cand 游客态与场景分流
- 类型: 业务规则风控
- 检测原理: `ComplianceServiceProvider.isGuestMode()` 拦截搜索；entry 场景（homepage_hangout/life/mall/poi）映射不同 scene code（30075/30122/9039x/90147）
- 对抗思路: 登录态与场景 entry 必须自洽，游客态/场景错配会直接短路
- 落地工具: 交叉引用 risk-control-adversary 业务规则风控（A3 §8）
- 证据等级: 已实证
- 置信度: 高
- 来源: projects/dy 2026-09-07 decompiled/.../discover/presenter/SearchAdvanceNetRequestPresenter.java

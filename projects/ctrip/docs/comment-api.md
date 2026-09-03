# 携程旅行 App 评论/点评接口逆向文档

> 目标：`ctrip.android.view`（携程旅行）v8.85.4 (versionCode 1989)
> 设备：Pixel 4 (flame) / Android 10 / arm64-v8a
> 结论先行：评论/点评列表走 SOA2 网关，核心服务 **`soa2/24077`**（点评核心）+ **`soa2/34308`**（酒店点评信息）。

---

## 1. 目标与结论摘要

| 项 | 值 |
|----|-----|
| App | 携程旅行 `ctrip.android.view` 8.85.4 |
| 网络栈 | OkHttp 4.9.1 + 自研 `CTHTTPClient`（SOA2 网关）+ 管道 SOTP/HTTP/QUIC |
| 点评列表页面 | **CRN（Ctrip React Native / Hermes）** 模块 `rn_xtaro_hotelCommentList` |
| 点评列表服务 | `https://m.ctrip.com/restapi/soa2/24077/h5-json/clientHotelCommentList` |
| 酒店点评信息 | `https://m.ctrip.com/restapi/soa2/34308/getHotelCommentInfo` |
| 签名 | `x-payload-source = baseSign(md5(body), "getdata")`（native `libctripenc.so`） |

> ⚠️ 关键结论：**评论/点评接口不在 Java/DEX 层**。酒店点评列表页面是 React Native 模块，
> 接口定义在 CRN bundle（`rn_xtaro_hotelCommentList/rn_business.jsbundle`，Hermes/MIXED）中，
> 通过 `ServiceConfigMap` 把客户端函数映射到 SOA2 的 `serviceId + serviceName`。
> Java 层只负责网络传输与签名（head / header / SOTP），业务参数由 RN 层构造。

---

## 2. 网络框架（Java 层）

### 2.1 请求框架类

| 层 | 类 | 说明 |
|----|----|----|
| 旧请求基类 | `ctrip.android.http.BaseHTTPRequest` | `getUrl()/getPath()/getParams()/getHead()`，反射收集字段为参数 |
| 新请求基类 | `ctrip.android.httpv2.CTHTTPRequest<M>` | `url/params/httpHeaders/enableEncrypt/disableSOTPProxy` |
| 核心客户端 | `ctrip.android.httpv2.CTHTTPClient` | `generateRequestDetail()` 组装 `RequestDetail` |
| 旧客户端 | `ctrip.android.http.CtripHTTPClientV2` | OkHttp 直发，`buildRequestHead()` |
| head 组装 | `ctrip.android.http.C13133k` | `m39924c()` 生成公共 head |
| 公共头实现 | `p1000yn.C28523b` | `mo86159a()`（head 字段）、`mo86161c()`（HTTP header） |

### 2.2 SOA2 URL 构造（RN 层 `getRequestUrl`）

```js
// rn_business.jsbundle 模块 666766
var u = disableJsonPath ? '' : `${jsonPath || 'h5-json'}/`;
// 生产(内地): https://m.ctrip.com/restapi/soa2/${serviceID}/${u}${serviceName}
// 国际版:      https://www.trip.com/restapi/soa2/${serviceID}/${u}${serviceName}
```

- 默认 jsonPath = **`h5-json`**（RN 业务层约定，注意区别于 Java 层的 `/json/` 或无中间路径）。
- `disableJsonPath:true` 时中间路径为空。
- 网关查询参数（Java 层自动追加）：`__gw_appid=99999999&__gw_ver=885.004&__gw_os=Android&__gw_platform=APP`。

---

## 3. 请求结构（动态抓包实证）

### 3.1 请求体（body = 公共 head + 业务参数）

```json
{
  "head": {
    "appid": "99999999",
    "auth":  "B40F1A89800BEA2F3A03BF93929B3E695DE8EC9EAD6EE04D6266F772B3AA0224",
    "cid":   "32001040290591014872",
    "ctok":  "",
    "cver":  "885.004",
    "lang":  "01",
    "sauth": "",
    "sid":   "8015",
    "syscode": "32"
  },
  "...业务参数（hotelId / sceneTypes / commentFilterOptions / ...）": "..."
}
```

head 字段由 `p1000yn.C28523b.mo86159a()` 生成（见 2.1），由 Java 层在 `serializeRequest` 时自动合并。

### 3.2 HTTP 请求头（关键）

| Header | 值/来源 |
|--------|---------|
| `User-Agent` | `Dalvik/..._CtripAPP_Android_8.85.4_..._SOAHTTP`（`DeviceUtil.getUserAgent() + "_SOAHTTP"`） |
| `x-trip-syscode` | `32`（系统码） |
| `x-trip-clientAppId` | `99999999` |
| `x-ctx-clientVersion` | `885.004` |
| `x-ctx-transactionId` / `trip-trace-id` / `x-ctx-replaytraceid` | UUID（追踪链） |
| `x-ctx-Currency/Locale/Region/Unit/Group` | `CNY` / `zh-CN` / `CN` / `METRIC` / `ctrip` |
| `x-payload-source` | **签名** = `baseSign(md5(body).toLowerCase(), "getdata")` |
| `x-payload-bnlabel` | token（`C22725a.m66703e()`） |
| `x-payload-bnlabel2` | tokenV2（`C22725a.m66700b()`，命中 URL 白名单时） |
| `cid` / `DUID` / `udl` / `cticket` / `cookie` / `GUID` | 设备/账号指纹 |

---

## 4. 评论/点评接口清单（`ServiceConfigMap`，来源 rn_business.jsbundle）

| 客户端函数 | SOA2 接口 | 说明 |
|-----------|-----------|------|
| `clientHotelCommentList` | `soa2/24077/h5-json/clientHotelCommentList` | **酒店点评列表（核心）** |
| `clientHotelOneComment` | `soa2/24077/h5-json/clientHotelOneComment` | 单条点评 |
| `clientGetMyCommentDetails` | `soa2/24077/h5-json/clientGetMyCommentDetails` | 我的点评详情 |
| `clientCommentTranslate` | `soa2/24077/h5-json/clientCommentTranslate` | 点评翻译 |
| `clientCommentUseful` | `soa2/24077/h5-json/clientCommentUseful` | 点评「有用」点赞 |
| `clientFavoriteComment` | `soa2/12465/h5-json/hotelFavoriteOperate` | 收藏点评 |
| `getHotelCommentInfo` | `soa2/34308/getHotelCommentInfo`（disableJsonPath） | 酒店点评汇总信息 |
| `getHotelAskInfo` | `soa2/34308/getHotelAskInfo`（disableJsonPath） | 酒店问答 |
| `getConversationUnreadMsgInfo` | `soa2/11679/getConversationUnreadMsgInfo`（disableJsonPath） | IM 未读 |
| `sdsdk` | `soa2/31454/sdsdk`（disableJsonPath） | 风控 sdsdk |
| `addIMPlusToken` | `soa2/23353/addIMPlusToken` | IM token |

> 另见：评论抽奖服务 `soa2/10342`（Java 层 `HotelUrlStaticResource.COMMENT_LOTTERY_DOMAIN`）。

---

## 5. 点评列表接口详解（`clientHotelCommentList`）

### 5.1 完整 URL

```
POST https://m.ctrip.com/restapi/soa2/24077/h5-json/clientHotelCommentList?__gw_appid=99999999&__gw_ver=885.004&__gw_os=Android&__gw_platform=APP
```

### 5.2 请求参数（`buildCommentListRequest` / `getCommentListRequest`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `hotelId` | int | 酒店 ID（如 `10650083138`） |
| `sceneTypes` | list | 场景类型 |
| `commentIdList` | list | 点评 ID 列表（定位到具体点评） |
| `hotelSemantic` | obj | 酒店语义 |
| `searchNodeInfo` | obj | 搜索节点信息（点评搜索页） |
| `extensionInfo` | obj | 扩展信息（AI 摘要场景：`sceneAiSummaryFilterCommonId` 等） |
| `abtResults` | list | ABT 实验结果 |
| `commentFilterOptions` | obj | 过滤选项（见 5.3） |
| `repeatComment` | int | 是否含追评（1/0） |
| `pageIndex` / `pageSize` | int | 分页；`pageSize` 默认 **10** |

### 5.3 `commentFilterOptions`（`buildCommentFilterOptions`）

| 字段 | 说明 |
|------|------|
| `pageIndex` | 页码 |
| `pageSize` | 每页条数（`getCommentListPageSize()` = 10） |
| `keyWord` | 搜索关键词 |
| `commonStatisticList` | `[主Tab, 子Tab]` 组合，如 `["7"]`(相似)、`["1"]`(全部)、`["6"]`(有图视频) |
| `rooms` | 房型过滤 |
| `travelTypes` | 出行类型过滤 |
| `filterDateTypeList` | 日期类型过滤 |
| `orderTypes` | 排序类型 |
| `repeatComment` | 追评 |
| `orderBy` | 排序（`selectedTagId == LATEST_LABEL_ID` 时 = `"1"`） |
| `commentTags` | 点评标签（`selectedTagId` 转字符串） |

### 5.4 枚举

```js
EMainTab: ALL=1, SIMILAR=7                       // 主 Tab：全部 / 相似点评
ESubTab:  ALL=-400, DEROGATORY=3, HASPICORVIDEO=6, FILTERBUTTON=-500
          // 子 Tab：全部 / 差评 / 有图有视频 / 筛选按钮
ExtensionKeyEnum: ChooseRelatedTagId, EmotionTagType
```

### 5.5 响应字段（业务模型，从 bundle 标识符提取）

`commentList / commentRating / commentRatingType / commentTagList / commentLevel / commentId /
commentContent / commentDate / userCommentLevel / usefulCount / nickName / imageInfosList /
additionalCommentText / commentsBeforeDecorationCount / commentsDuringTrialOperationCount /
hotelCommentInfo / similarCommentRating / negativeCommentSummary / verifiedReviews ...`

---

## 6. 签名机制（`x-payload-source`）

生成点（`CTHTTPClient.generateRequestDetail`，Java）：

```java
map.put("x-payload-source",
    C22725a.m66709k(StringUtil.getMD5(requestDetail.bodyBytes).toLowerCase(Locale.ENGLISH)));
```

`C22725a`（混淆名 `hj0.a`，类内 LogTag `BaseSign`）→ `m66709k(str)` 委托接口实现：

```java
strMo54118e = f68038d.mo54118e(str.getBytes(), "getdata");
// str = md5(body) 的 32 位小写 hex；操作类型 "getdata"
```

`f68038d` 是 `hj0.C22725a.a` 接口的实例，通过 `m66707i()` 注册，**实际实现是动态加载的 native so**
（对应 `libctripenc.so` / `libapp.so` / `libhke.so` 之一），所以：

- `x-payload-source` = **native `baseSign(md5(body), "getdata")`**，输出 72 位 hex（实测样例
  `C85B162EB3128973D7039908AE2D6AE95CC2916A14E...`，前 32 位为常量前缀 + 后 40 位随 body 变化）。
- `x-payload-bnlabel` / `x-payload-bnlabel2` = native `getToken()` / `getTokenV2()`。
- 完整还原该签名需对 native so 做 IDA / unidbg 分析（**protocol-signature-reverser 范畴**）。

> ✅ **签名已完整逆向**（详见 [signature.md](signature.md)）：
> `x-payload-source = libscmain.so 的 native simpleSign(md5(body), "getdata")`，输出 75 hex =
> `[32 hex 设备密钥指纹] + [11 hex 会话态] + [32 hex keyed 运算]`。绑定 Android Keystore 硬件密钥
> （secp256r1 ECDSA）+ 会话态 → **纯离线不可行**，已落地**策略 E（Frida RPC 在线签名 oracle）**，
> 见 `hooks/sign_rpc.js` + `scripts/sign_oracle.py`（已验证）。

---

## 7. 调用链

```
RN 页面 xtaro_hotel_comment_list (Hermes/MIXED JS)
  └─ requestClientHotelCommentList()
       └─ fetch(t, ServiceConfigMap.clientHotelCommentList)        // t = 业务参数
            ├─ getRequestUrl()   → https://m.ctrip.com/restapi/soa2/24077/h5-json/clientHotelCommentList
            └─ getRequestParams() → body 业务参数（hotelId / commentFilterOptions / ...）
                 └─ 原生桥 → ctrip.android.httpv2.CTHTTPClient
                      ├─ generateRequestDetail()
                      │    ├─ serializeRequest()：合并 head(appid/auth/cid/.../syscode) + 业务参数
                      │    └─ 组装 httpHeaders（x-trip-syscode / x-ctx-* / x-payload-source=baseSign(md5(body))）
                      └─ SOTP/HTTP 管道 → OkHttp 4.9.1 → m.ctrip.com
```

页面入口（Java）：`HotelCommentListActivity` → `HotelRNHostUtil.getUrl("/rn_xtaro_hotelCommentList/main.js?CRNType=1&CRNModuleName=xtaro_hotel_comment_list&HotelBaseInfo=<urlencoded>")`。

---

## 8. 关键文件索引

| 产物 | 路径 |
|------|------|
| APK | `projects/ctrip/apk/ctrip-8.85.4.apk` |
| 反编译源码 | `projects/ctrip/decompiled/sources/` |
| 点评 CRN bundle（明文 JS） | `projects/ctrip/capture/commentlist.jsbundle` |
| 点评 CRN bundle（Hermes 字节码） | `projects/ctrip/capture/commentlist.hbcbundle` |
| Frida 抓包 Hook | `projects/ctrip/hooks/capture_review_api.js` |
| 抓包日志 | `projects/ctrip/capture/review_api_capture.log` |
| 扫描脚本 | `projects/ctrip/scripts/scan_review_endpoints.py` |

关键反编译类：
- `ctrip/android/http/BaseHTTPRequest.java`
- `ctrip/android/httpv2/CTHTTPClient.java`（`generateRequestDetail` / `RequestDetail`）
- `ctrip/android/httpv2/CTHTTPRequest.java`
- `ctrip/android/http/C13133k.java`（head 组装）
- `p1000yn/C28523b.java`（head 字段 + HTTP header）
- `hj0/C22725a.java`（BaseSign，`x-payload-source` 签名委托）

---

## 9. 合规声明

本文档仅用于**安全研究 / 自有应用调试 / 教育**用途。请求签名（`baseSign`）与服务端风控
（SOTP、sdsdk、设备指纹、频控）未授权时请勿用于生产数据抓取；遵守《网络安全法》《个人信息保护法》
及携程服务条款。

---
*生成时间：2026-08-28 · 逆向工作台 DSH · skill: android-recon + android-dynamic*

# 携程（ctrip.android.view 8.85.4）风控对抗方案

> 生成日期: 2026-08-28 | 资料基线: docs/comment-api.md、docs/signature.md、capture/review_api_capture.log、capture/sign_capture.log、so_analysis/libscmain.so（字符串分析）| 公开情报: [携程业务安全官方分享](https://cloud.tencent.com.cn/developer/article/1063141)、[携程滑块点选验证码逆向](https://blog.csdn.net/qq_36551453/article/details/156152536)、[携程机票API反爬](https://datasea.cn/go0210477834.html) | 知识库: E-01~E-12

## 一、接口总览

| 接口ID | URL/端点 | 方法 | 业务含义 | 签名头 | 参数加密 | 频率特征 | 环境检测 |
|---|---|---|---|---|---|---|---|
| IF-01 | /restapi/soa2/24077/h5-json/clientHotelCommentList | POST | 酒店点评列表（核心） | 有 x-payload-source | 无（enableEncrypt=false） | 翻页 | 有（so 层） |
| IF-02 | /restapi/soa2/24077/h5-json/clientHotelOneComment | POST | 单条点评 | 有 | 无 | 低频 | 有 |
| IF-03 | /restapi/soa2/24077/h5-json/clientGetMyCommentDetails | POST | 我的点评详情 | 有 | 无 | 低频 | 有 |
| IF-04 | /restapi/soa2/24077/h5-json/clientCommentTranslate | POST | 点评翻译 | 有 | 无 | 低频 | 有 |
| IF-05 | /restapi/soa2/24077/h5-json/clientCommentUseful | POST | 点评「有用」点赞 | 有 | 无 | 低频 | 有 |
| IF-06 | /restapi/soa2/12465/h5-json/hotelFavoriteOperate | POST | 收藏点评 | 有 | 无 | 低频 | 有 |
| IF-07 | /restapi/soa2/34308/getHotelCommentInfo | POST | 酒店点评汇总（详情页摘要） | 有 | 无 | 随详情加载 | 有 |
| IF-08 | /restapi/soa2/34308/getHotelAskInfo | POST | 酒店问答 | 有 | 无 | 低频 | 有 |
| IF-09 | /restapi/soa2/11600/heartBeat.json | POST | 心跳 | 有 | **有**（body 含加密 key） | 周期 | 有 |
| IF-10 | /restapi/soa2/13916/json/tripAds | POST | 广告（设备指纹上报载体） | 有 | 无 | 高频 | 有 |
| IF-11 | /restapi/soa2/23196/json/getServerIP | POST | 服务器 IP 调度 | 有 | 无 | 启动期 | 有 |
| IF-12 | /restapi/soa2/24862/validateTicket | POST | 票据校验（鉴权） | 有 | 无 | 启动期 | 有 |
| IF-13 | /restapi/soa2/18088/getAppStaticResource | POST | 静态资源配置 | 有 | 无 | 启动期 | 有 |

> 签名头统一为 `x-payload-source`（75 hex）；另有 `x-payload-bnlabel`/`x-payload-bnlabel2` token 头（按 URL 白名单附加）。SOTP 管道（PipeType.SOTP）覆盖多数请求。

## 二、逐接口风控分析

### IF-01 点评列表（核心目标接口）

**请求特征**：`POST /restapi/soa2/24077/h5-json/clientHotelCommentList?__gw_appid=99999999&__gw_ver=885.004&__gw_os=Android&__gw_platform=APP`；body = 公共 head（appid/auth/cid/ctok/cver/lang/sauth/sid/syscode）+ 业务参数（hotelId、sceneTypes、commentFilterOptions{pageIndex,pageSize=10,keyWord,commonStatisticList,rooms,travelTypes,orderTypes,...}、commentIdList、extensionInfo、abtResults）。样本见 capture/review_api_capture.log。

**风控点**

| 维度 | 检测机制 | 证据等级 | 证据 |
|---|---|---|---|
| 签名校验 | x-payload-source 设备+会话绑定签名，body 变化即签名变 | 已实证 | docs/signature.md §3（75hex 三段式） |
| 请求策略与行为画像 | 翻页频控、评论列表访问路径（详情→点评） | 推测 | 无实测阈值，待对拍 |
| 设备指纹 | 请求头 DUID/udl/cid/GUID/cticket 一致性 | 已实证 | capture 日志头部 |

**对抗手段**（P0→P3）

| 风控点 | 手段 | 落地工具 | 优先级 |
|---|---|---|---|
| 请求策略 | 拟人化翻页节奏 + 详情→点评行为序列 | 本 skill 策略 + 采集脚本 | P0 |
| x-payload-source | Frida RPC 在线签名 oracle | hooks/sign_rpc.js + scripts/sign_oracle.py | P1 |
| 设备指纹 | 真机保真（指纹取自同一设备，不混用） | 真机 + 采集脚本 | P2 |

**验证步骤**：spawn 注入 oracle → 对真实 hotelId 逐页请求（pageIndex 递增）→ 通过标准：连续翻页 status=200 且返回非重复评论、无 403/429/蜜罐数据。

**失败模式与坑**：① attach 热注入触发反检测（script destroyed），必须 spawn 冷注入；② 直接打裸评论接口跳过「详情页」前置请求，序列异常易触发画像（见 §四）。

### IF-09 心跳（含参数加密）

**请求特征**：`POST /restapi/soa2/11600/heartBeat.json`；body 含加密 `key` 字段（Base64，长度约 700+，随会话变化），head 之外还带 `extension` 数组。

**风控点**：参数加密（`key` 字段加密，已实证）；心跳节律是否校验（推测）。

### IF-10 广告（设备指纹上报载体）

**请求特征**：`POST /restapi/soa2/13916/json/tripAds`；body 的 `device` 段承载完整设备指纹（见 §三）。

**风控点**：设备指纹上报（已实证）——此接口是风控侧采集设备画像的主通道。

## 三、全局风控面（跨接口）

### 3.1 签名体系（已破，策略 E）

- 现状：`x-payload-source = libscmain.so native simpleSign(md5(body), "getdata")`，75 hex = `[32hex 设备密钥指纹] + [11hex 会话态] + [32hex keyed 运算]`。绑定 Android Keystore（secp256r1 ECDSA 硬件密钥）+ 会话态，**纯离线不可行**。
- 对抗：Frida RPC 在线签名（hooks/sign_rpc.js，已验证）。签名能力必须服从请求策略（oracle 调用也限频、错峰）。

### 3.2 设备指纹（已实证，四类采集面）

tripAds body `device` 段实测字段：`androidid/androididMd5/brand/carrier/connectionType/deviceType/did/didMd5/dpi/geo{coordinateType,latitude,longitude,type,utcOffset}/height/hwv/ip/ipv6/language/localTzName/mac/macMd5/make/mode/os/osv/pixelRatio/romVersion/ssid/ua/width/wifiMac`；请求头另有 `DUID/udl/cid/cticket/GUID`。

- 对抗：真机保真（整套指纹取自同一物理设备），不混用改机/沙箱（部分字段矛盾本身即检测点，E-05）。换设备 = 换全套指纹。

### 3.3 埋点/行为画像（已实证字段，强校验程度推测）

请求头实测：`x-ctx-ubt-vid=77019A70A2FF11F1F7264B115A5541FC / x-ctx-ubt-pageid=sdk_app_launch / x-ctx-ubt-pvid / x-ctx-ubt-sid`；另有 `x-ctx-transactionId / trip-trace-id / x-ctx-replaytraceid` 追踪链。

- 对抗：调业务接口前补前置埋点（打开页面→埋点→接口），埋点链路与真实 App 一致（E-12）；行为心跳与交互路径仿真（E-11）。

### 3.4 环境检测（已实证，so 层）

`libscmain.so` 字符串实测：多开/虚拟环境检测（`com.yooha.antisdk.MainActivity`/`com.shaker.wxxh.moli.fs`/`com.trigtech.privateme`/`godinsec_private_space`/`multiaccount`/`ldAppStore`/`/system/priv-app/`）；设备指纹采集（`getActiveCpuCount/getBatteryStatus/getScreenBrightness/...`）；Android Keystore 硬件密钥（`secp256r1`+`DIGEST_SHA256`）。

- 已实证反 Frida：attach 热注入 → `script has been destroyed`（进程被反检测处理）；spawn 冷注入可存活。
- 对抗：spawn 注入错开冷启动检测窗口；真机基线（Pixel 4 + APatch）保持环境自洽。

### 3.5 传输层（已实证）

- SOTP 管道（`PipeType.SOTP`，多数请求）+ `enableEncrypt` 标志 + heartBeat 加密 `key` 字段。
- 对抗：SOTP 由原生 CTHTTPClient 处理，无需绕过（走 App 原生网络层即自动满足）；不走裸 HTTP 重放（会缺失 SOTP 封装特征）。

## 四、请求策略与真人模拟（核心）

### 逆向期（分析/采集/验证期间风险最小化）

| 风险动作 | 风控后果 | 规避策略 |
|---|---|---|
| oracle 高频调用（连续签名对拍） | 设备级限流/拉黑，污染后续采集 | 限频（间隔 ≥1s）、错峰、与真实浏览交织；用不同 hotelId 轮换 |
| attach 热注入 | 触发反检测（script destroyed） | 一律 spawn 冷注入，注入后等待 App 完成冷启动检测窗口 |
| 采集节奏过快（评论逐页猛拉） | 翻页频控/蜜罐 | 翻页间隔拟人化（≥0.8s 起步），dry-streak 跳带 |
| 同设备反复清数据/换账号 | 设备-账号绑定画像异常 | 保持账号-设备绑定一致，不频繁切换 |

### 数据期（正式拿数据的长期策略）

- **节奏**：翻页间隔拟人化随机（基准 1.5~3s，加 ±30% 抖动，避免整点分钟与完全均匀）；单设备日请求预算保守起步（如单酒店点评全量拉取 ≈ 数十页，控制在日预算内）；dry-streak 跳带（连续 3 页空结果则跳过该酒店，模拟失去兴趣）。
- **序列**：目标请求前打真实行为路径——`getAppStaticResource/getServerIP/validateTicket`（启动预热）→ `tripAds`（指纹上报）→ `getHotelCommentInfo`（详情页摘要，先于列表）→ `clientHotelCommentList`（点评列表翻页）。直接打裸列表接口序列本身即特征（E-12）。
- **会话**：`cticket`（登录票据）/`cid`/`DUID` 在其生命周期内使用；多账号轮换时保持账号-设备绑定一致（同设备不高频切号，同账号不跨多 IP）。
- **参数完整性**：全套请求头与真实 App 一致（UA 含 `_SOAHTTP`、x-ctx-Currency/Locale/Region/Unit/Group、x-trip-syscode、x-trip-clientAppId、x-ctx-ubt-*、DUID/udl/cid/cticket/GUID、trip-trace-id）；body 的 head 字段（appid/auth/cid/ctok/cver/lang/sauth/sid/syscode）完整；可选参数（extensionInfo/abtResults/commentFilterOptions 全字段）不省略。
- **设备-IP-账号一致性**：出口 IP 与设备归属一致；避免同 IP 多账号、同账号多 IP（交叉污染是画像特征，E-04）。
- **频率预算**：单设备/单账号日请求量控制在真人量级（点评浏览场景几十~几百请求/天）；增速缓慢、灰度观察（E-10）。
- **监控与止损**：封禁信号 = 403/429/返回码异常/评论列表不更新或内容错乱（蜜罐 E-03）；命中即弃用该会话/IP/设备，进入退避；预留账号轮换梯度。

## 五、对抗策略优先级

| 顺序 | 动作 | 成本×收益 | 止损条件 |
|---|---|---|---|
| 1 | 请求策略 + 真人模拟（节奏/序列/会话/参数完整） | 低×高 | 无（纯策略调整） |
| 2 | 签名：Frida RPC oracle（已完成） | 低×高 | oracle 进程被杀需重注入 |
| 3 | 设备指纹：真机保真 | 中×中 | 换设备需重提全套指纹 |
| 4 | 环境检测：spawn 注入 + 真机基线 | 中×中 | 反检测升级需跟进 android-dynamic |

## 六、验证记录

| 日期 | 验证项 | 手段 | 结果 | 证据路径 |
|---|---|---|---|---|
| 2026-08-28 | 签名 oracle 可用性 | spawn 注入 + RPC 调 sign() | 通过（返回 75hex 签名） | capture/sign_capture.log |
| 2026-08-28 | attach 反检测 | attach 热注入 | 失败（script destroyed）→ 改 spawn | 本次逆向过程 |
| 2026-08-28 | **重放验证** getServerIP | Python 重放 + oracle 签名 | **通过**：200 Ack:Success（签名/head/headers 链路打通，登录态有效） | scripts/replay_test.py |
| 2026-08-28 | **频控对拍** getServerIP | 批量签名 + 0.3s 间隔连续 8 请求 | **无频控**：8/8 全部 200，响应时间戳递增（非缓存/蜜罐） | scripts/replay_test.py --mode rate |
| 2026-08-28 | **埋点强校验** getServerIP | full/drop/tamper 三态对照 | **不强校验**：删除/篡改 x-ctx-ubt-* 均 200 Success | scripts/replay_test.py --mode ubt |
| 2026-08-28 | oracle 连续调用反检测 | 连续 RPC sign()（0.4s 间隔） | 触发反检测（script destroyed）→ **批量签名 batchSign 一次拿多签名规避** | 本次实测 |
| 2026-08-28 | 点评列表 clientHotelCommentList | 构造 body + 签名重放 | **签名验证通过**（服务端 Ack:Failure 但错误为业务层反序列化 FXD302000，非签名非法）；body 字段结构待修正 | scripts/replay_test.py --mode comment |
| 2026-08-29 | 点评 body 结构修正 | 定位反序列化根因 | **hotelId 是 int 类型**（>2^31 反序列化失败）；body 是 getCommentListRequest 扁平结构（非嵌套 commentFilterOptions） | 实测定位 |
| 2026-08-29 | **点评列表调通** | hotelId=431041 重放 | **成功**：返回完整点评数据（clientHeader + 点评） | scripts/replay_test.py --mode comment |
| 2026-08-29 | **点评翻页频控对拍** | hotelId=431041，0.5s 间隔翻页 7 页 | **无频控**：page1~7 全部 200 | scripts/replay_test.py --mode comment |

## 七、泛化经验提炼

本次新增 general-principles.md 条目：E-13（见知识库）。

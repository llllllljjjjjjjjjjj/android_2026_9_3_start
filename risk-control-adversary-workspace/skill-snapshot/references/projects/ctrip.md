# ctrip 风控记录

- 状态: 方案已生成（签名已破，请求策略待对拍）
- 最后更新: 2026-08-28
- 方案文档: projects/ctrip/docs/risk-control-plan.md

## 接口风控速查表

| 接口ID | 端点 | 风控维度 | 对抗手段 | 状态 | 证据 |
|---|---|---|---|---|---|
| IF-01 | soa2/24077/h5-json/clientHotelCommentList | 签名+设备指纹+请求策略 | RPC oracle + 拟人节奏 | 已破 | signature.md + replay_test.py |
| IF-02~05 | soa2/24077/h5-json/client* | 签名（同体系） | RPC oracle | 进行中 | ServiceConfigMap |
| IF-06 | soa2/12465/h5-json/hotelFavoriteOperate | 签名 | RPC oracle | 进行中 | ServiceConfigMap |
| IF-07 | soa2/34308/getHotelCommentInfo | 签名（disableJsonPath） | RPC oracle | 进行中 | ServiceConfigMap |
| IF-09 | soa2/11600/heartBeat.json | 参数加密（key 字段） | 走原生层 | 未动 | capture 日志 |
| IF-10 | soa2/13916/json/tripAds | 设备指纹上报 | 真机保真 | 已破（指纹提取） | capture 日志 device 段 |

状态取值：已破 / 进行中 / 未动 / 死路。

## 请求策略实测数据（黄金素材）

| 日期 | 参数 | 实测值/阈值 | 证据 |
|---|---|---|---|
| 2026-08-28 | 签名 oracle 单次调用 | 正常返回 75hex，未测频控上限 | capture/sign_capture.log |
| 2026-08-28 | attach 热注入 | 反检测 script destroyed | 本次逆向过程 |
| 2026-08-28 | getServerIP 重放 | 200 Ack:Success（签名链路打通） | scripts/replay_test.py |
| 2026-08-28 | getServerIP 频控 | 0.3s×8 全部 200 无频控 | scripts/replay_test.py --mode rate |
| 2026-08-28 | getServerIP 埋点强校验 | full/drop/tamper 均 200，**不强校验** | scripts/replay_test.py --mode ubt |
| 2026-08-28 | oracle 连续 RPC 调用 | 0.4s 间隔触发反检测 → batchSign 批量签名规避 | 本次实测 |
| 2026-08-28 | clientHotelCommentList | 签名验证通过，body 反序列化 FXD302000 待修 | scripts/replay_test.py --mode comment |
| 2026-08-29 | 点评 body 结构 | **hotelId 是 int（>2^31 失败）；扁平结构（getCommentListRequest）** | 实测定位 |
| 2026-08-29 | 点评列表调通 | hotelId=431041 返回完整点评数据 | scripts/replay_test.py |
| 2026-08-29 | 点评翻页频控 | 0.5s 间隔翻页 7 页全部 200 **无频控** | scripts/replay_test.py |

## 公开情报（Web）

| 日期 | 主题 | 要点 | 来源 URL |
|---|---|---|---|
| 2026-08-28 | 携程业务安全官方分享 | 携程有独立业务安全体系（风控/反爬） | https://cloud.tencent.com.cn/developer/article/1063141 |
| 2026-08-28 | 携程滑块点选验证码 | 登录有滑块/图标点选验证码（Web 端） | https://blog.csdn.net/qq_36551453/article/details/156152536 |
| 2026-08-28 | 携程机票 API 反爬 | 机票数据有反爬策略 | https://datasea.cn/go0210477834.html |

## 关键结论

1. 签名 `x-payload-source` 绑 Android Keystore 硬件密钥（secp256r1 ECDSA）+ 会话态 → 纯离线死路，在线 RPC oracle 是唯一可行解。
2. 设备指纹全集集中暴露在广告上报接口 `tripAds` 的 device 段（androidid/brand/carrier/dpi/hwv/os/osv/ssid/... 约 20+ 字段）+ 请求头 DUID/udl/cid/cticket/GUID。
3. 埋点字段 `x-ctx-ubt-*`（vid/pageid/pvid/sid）+ transactionId/trace-id 构成行为追踪链，脱机直调缺失。
4. `libscmain.so` 内置多开/虚拟环境检测（yooha.antisdk/moli.fs/trigtech.privateme/godinsec/multiaccount 等）+ 反 Frida（attach 触发 script destroyed）。
5. 评论列表是 RN 模块，业务参数在 CRN bundle；直接打裸接口跳过「详情页→点评」行为路径是明显画像特征。
6. 点评接口 body 是扁平结构（getCommentListRequest，非嵌套 commentFilterOptions），hotelId 是 **int 类型**（>2^31 反序列化失败 FXD302000）；点评请求走 RN Networking（Chromium CookieManager），非 CTHTTPClient 普通路径。
7. 频控实测：getServerIP 0.3s×8、点评列表 0.5s×7 均无频控；埋点 x-ctx-ubt-* 删/改不强校验。

## 失败模式

| 日期 | 场景 | 失败原因 | 教训 |
|---|---|---|---|
| 2026-08-28 | attach 热注入 frida | 触发 libscmain.so 反检测 | 一律 spawn 冷注入，错开冷启动检测窗口 |
| 2026-08-28 | frida spawn 报 ServerNotRunningError | adb server 重启丢 forward | Python 内 os.system 自建 forward + pidof 回退 |

## 泛化提炼（L3 → L1 沉淀登记，见 general-principles.md §0.4）

| 日期 | 类型 | 编号 | 泛化角度 |
|---|---|---|---|
| 2026-08-28 | 新增 E | E-13 | 上报/广告接口集中暴露设备指纹全集（已实证/高） |
| 2026-08-28 | 新增 E | E-14 | 签名 oracle 调用本身需纳入请求策略（已实证/高） |
| 2026-08-28 | 新增 F | F-01 | attach 热注入触发反检测，硬目标一律 spawn 冷注入（已实证/高） |

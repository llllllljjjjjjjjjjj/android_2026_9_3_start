# dzdp 风控记录

- 状态: 方案已生成（签名/请求/解密/解析全链路已破；列表接口待住宅 IP 验证）
- 平台: Android
- 最后更新: 2026-08-30
- 方案文档: projects/dzdp/docs/risk-control-plan.md

## 接口风控速查表

| 接口ID | 端点 | 风控维度 | 对抗手段 | 证据等级 | 状态 | 证据 |
|---|---|---|---|---|---|---|
| IF-01 | /review/shopreviewlist.bin | 签名+IP×路径规则 | RPC oracle + 住宅IP+节奏 | 已实证 | 待住宅IP | capture/review_resp.bin(首200) |
| IF-02 | /review/siftedreviewlist.bin | 同上 | 同上 | 已实证 | 待住宅IP | capture/req_trace.log |
| IF-05 | /review/shopaudioreviewlist.bin | 同上 | 同上 | 已实证 | 待住宅IP | capture/req_trace.log |
| IF-07 | /review/batchgetreviewlistask.bin | 签名(弱) | oracle | 已实证 | 已破 | 数据中心IP 200 |
| IF-08 | /review/shopugc.bin | 签名+加密id | oracle + 参数完整 | 已实证 | 已破 | 200+JSON解析 |
| IF-09 | /review/aicustomsummary.bin | 签名(弱) | oracle | 已实证 | 已破 | 数据中心IP 200 |
| IF-06 | /review/reviewtaglist.bin | 业务(-109) | 参数完整 | 已实证 | 未动 | 非WAF 403 |
| IF-10 | /actionlog/useraction.bin | 签名 | oracle | 已实证 | 已破 | POST 上报 |

状态取值：已破 / 进行中 / 未动 / 死路（附一句原因）。

## 请求策略实测数据（黄金素材，保留原始数字）

| 日期 | 参数 | 实测值/阈值 | 证据 |
|---|---|---|---|
| 08-30 | 首次请求 | WiFi直连(住宅) + RPC签名 → HTTP 200 | capture/review_resp.bin |
| 08-30 | 高频连发 | 30s 内多请求 → 路径级 403(openresty) | capture/req_trace.log |
| 08-30 | 数据中心IP×list接口 | 美国/香港节点 4 个 *list 接口全 403 | 本方案 §六 |
| 08-30 | 数据中心IP×非list接口 | shopugc/aicustomsummary/batchgetreviewlistask 200 | 本方案 §六 |
| 08-30 | 换设备标识 | pm clear 后新 uuid/dpid + 香港IP → *list 仍 403 | 本方案 §六 |
| 08-30 | 原住宅IP回连 | 2h+ 后仍 403（窗口未过） | 本方案 §六 |
| 08-30 | 响应加密 | AES/CBC/NoPadding(密钥XOR链) + gzip → DPObject('O') | scripts/mapi_crypto.py |
| 08-30 | DPObject 字段ID | = 字段名 Java hashCode 16位混合 | scripts/dp_parser.py |

## 公开情报（Web，与本地资料分开，标注可信度）

| 日期 | 主题 | 要点 | 可信度 | 来源 URL |
|---|---|---|---|---|
| 08-30 | 大众点评反爬 | mtgsig 签名是核心门槛；风控含 IP/频率/行为 | 中(社区) | https://blog.csdn.net/weixin_42558257/article/details/160847601 |
| 08-30 | 美团/点评采集代理 | 代理 IP 选择影响存活率 | 中(社区) | https://blog.csdn.net/tang77789/article/details/160560865 |

## 关键结论

1. 签名体系：mtgsig(Babel V4,native) + csec 参数 + cx 指纹 —— RPC oracle 可生成，服务端接受（首 200 实证）。
2. 响应加密链：AES/CBC/NoPadding（密钥 XOR 链还原）→ gzip → DPObject（字段 ID = 字段名哈希）—— 全链路 Python 已实现。
3. **列表接口（*list.bin）被 WAF「出口 IP × 路径」规则拦截：数据中心 IP 一律 403，住宅 IP 需低频拟人；封禁不随设备标识更换清除（F-02）。**
4. 非列表接口（问大家/AI摘要/UGC）数据中心 IP 可通（F-03），可作预热与兜底数据源。
5. App 原生请求栈（RPC fetch）与 Python 直连在签名层等效；WAF 层看 IP×路径而非客户端特征。

## 失败模式

| 日期 | 场景 | 失败原因 | 教训 | 关联 F 条目 |
|---|---|---|---|---|
| 08-30 | 高频请求触发 403 | 30s 内连发列表接口 | 列表接口必须低频+住宅IP | F-02 |
| 08-30 | 换 VPN 节点尝试解封 | 数据中心 IP 被规则拦截 | 换 IP 前先验 IP 类型 | E-26 |
| 08-30 | 清数据换设备标识 | 封禁不在设备维度 | 别动设备标识，先查 IP | F-02 |
| 08-30 | 辅助接口 200 误判解封 | 规则只拦列表热点 | 以主接口 200 为判据 | F-03 |

## 泛化提炼（L3 → L1 沉淀登记，见 general-principles.md §0.4）

| 日期 | 类型 | 编号 | 泛化角度 |
|---|---|---|---|
| 2026-08-30 | 新增 E | E-26 | 数据中心 IP × 列表接口规则拦截，住宅 IP 是唯一解（已实证/高） |
| 2026-08-30 | 新增 F | F-02 | 路径级频控封禁绑定「IP×路径」，不随设备标识更换清除（已实证/高） |
| 2026-08-30 | 新增 F | F-03 | 辅助接口放行 ≠ 解封，以主接口 200 为验证判据（已实证/中） |

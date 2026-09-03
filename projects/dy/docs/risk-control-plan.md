# 抖音（dy.apk 38.0.0）风控对抗方案

> 生成日期: 2026-08-28 | 资料基线: README.md / docs/search_api.md / docs/signature_structure.md / docs/amemv-cert-bypass.md / capture/charles_session4,5.json / hooks/dy_hook21,30,34,35 / scripts/dy_search.py,replay_search.py | 知识库: general-principles.md 当前 E-16 条

## 一、接口总览

| 接口ID | URL/端点 | 方法 | 业务含义 | 签名头 | 参数加密 | 频率特征 | 环境检测 |
|---|---|---|---|---|---|---|---|
| IF-01 | /aweme/v2/search/general/stream/ | POST | 主搜索（首屏+翻页） | 八神+stub | body zstd（x-bd-content-encoding） | 身份级频控 hit_shark | metasec 反 hook/反枚举 |
| IF-02 | /aweme/v2/search/general/single/ | POST | 主搜索单请求版 | 同上 | 同上 | 同上 | 同上 |
| IF-03 | /aweme/v1/search/sug/ | GET | 联想词 | 同上 | query 明文 | 低 | 同上 |
| IF-04 | /aweme/v1/search/refresh_related_search/ | GET | 相关搜索刷新 | 同上 | query 明文 | 低 | 同上 |
| IF-05 | /aweme/v1/search/history_words_get|record/ | GET/POST | 搜索历史读写 | 同上 | body JSON | 低 | 同上 |
| IF-06 | /aweme/v1/search/memory/upload_ei_feature/ | POST | 行为埋点（search_id） | 同上 | body zstd | 随行为 | 同上 |

## 二、逐接口风控分析

### IF-01/IF-02 主搜索 general/stream|single

**请求特征**：POST `https://search5-search-m-hj.amemv.com/aweme/v2/search/general/{stream|single}/`；query 含 klink_egdi+全套设备参数+动态 _rticket/ts；body=zstd(x-www-form-urlencoded)，头 `x-bd-content-encoding: zstd` + `ttzip-version: search_api`；cookie 为登录态全家桶（sessionid/sid_tt/odin_tt/passport_mfa_token/bd-ticket-guard 系列）。样本：capture/charles_session4.json entry63、charles_session5.json entry74；body 明文 capture/search_bodies/charles_2_0b.zstd（13784B 登录态）、entry74 明文（2283B 游客态）。

**风控点**

| 维度 | 检测机制 | 证据等级 | 证据 |
|---|---|---|---|
| 签名校验 | 八神头每请求变化，Gorgon 4B=keyed-hash(query)+ctx 轮换 | 已实证 | docs/signature_structure.md |
| 参数加密 | body/响应 zstd 压缩（预训练字典 template_dict_v1.zstdict） | 已实证 | capture/search_bodies/*.zstd |
| 设备指纹 | 八神 Medusa/Helios 含设备指纹分量；body 需全量设备参数 | 已实证 | 最小 body→hit_shark；全量→通过 |
| 请求策略与行为画像 | 身份级频控 hit_shark；~120 连发→设备拉黑（App -20013）；verbatim 重放二次即 hit_shark | 已实证 | 2026-08-27/28 实验记录 |
| 环境检测 | metasec 反 frida 枚举（SF-016）+ checksum 反 hook | 已实证 | docs/notes.md §5.5 |

**对抗手段**

| 风控点 | 手段 | 落地工具 | 优先级 |
|---|---|---|---|
| 请求策略 | 拟人化节奏：≥3-5s 随机间隔、单会话低频、先 sug/history 预热再 general、翻页同 search_session_id | dy_search.py 节奏参数 | P0 |
| 八神签名 | RPC oracle 在线签名（libmetasec+0x28065c）+ x-ss-stub 复用 | hooks/dy_hook21.js | P1 |
| 参数完整性 | 全量参数模板（entry74 明文 2283B 参数集）+ 真实 cookie 会话 + 全套头（bd-ticket-guard 等复用抓包值） | dy_search.py load_template() | P1 |
| 设备指纹 | 保持 device_id/install_id/cookie/八神 同源自洽；换词换 session_id 防重放 | scripts 参数 | P2 |
| 环境检测 | hook30 FORGE 证书绕过 + QUIC 降级 + florida-server 免杀 | hooks/dy_hook30_probe.js | P3 |

**验证步骤**：全量重放（replay_search.py，URL/body/headers 原样只换八神）→ 通过标准：status_code=0 且 log_pb.stab_extra.NilInfoContext 为空。
**失败模式与坑**：① body 必须是 zstd（无 x-bd-content-encoding 标记→empty_query）；② 最小 body 缺设备指纹参数→hit_shark；③ 同 URL+同 body 连续重放→hit_shark（重复检测）；④ 换 ts/_rticket 后 bd-ticket-guard-client-data 旧值可能失配；⑤ PC 直连需 trust_env=False（Windows 系统代理被 Charles 占用时自签证书失败）。

### IF-03~IF-06 附属接口

**请求特征**：GET 类 keyword 在 query（sug/refresh_related/history_words_get）；POST 类 body 为 JSON（history_words_record）或 zstd（upload_ei_feature）。
**风控点**：签名校验同八神；频率特征低；行为画像：埋点接口（upload_ei_feature）缺失可能削弱行为拟真。
**对抗手段**：主搜索前先打 history_words_get + sug 模拟真实进入路径（P0）。
**验证步骤**：与主搜索同节奏联调 → 通过标准：status=0。
**失败模式与坑**：埋点类接口带 search_id，翻页时用同 search_session_id 关联。

## 三、全局风控面（跨接口）

- **设备指纹**：八神 X-Medusa（~910B 疑似 AES-GCM 设备指纹 payload）+ X-Helios 全输入敏感；body 参数集即客户端指纹（device_score/realtime_feature_channel/bcm_chain/client_server_extra/template_extra_info 等）。证据：已实证（参数缺失→hit_shark）。
- **环境检测**：libmetasec_ml.so VMP + 275064 区 checksum 反 hook + frida 反枚举（进程表隐身，SF-016）。证据：已实证。
- **签名体系**：VMP 核心+ctx ~0.5-0.6s 轮换 → 纯离线不可行，交付形态=在线 oracle（策略 H）。证据：已实证（docs/signature_structure.md）。
- **请求策略**：身份级频控阈值未知（保守按 >10 次/分钟触发，待对拍）；设备拉黑可被 `pm clear` 重置（丢登录态）。证据：已实证（8/28 pm clear 后恢复）。

## 四、请求策略与真人模拟（核心）

**逆向期（分析/采集/验证期间的风险最小化）**

| 风险动作 | 风控后果 | 规避策略 |
|---|---|---|
| oracle 高频调用 | 设备级限流/拉黑（8/27 00:31 ~120 连发实证） | oracle 调用限频（≥2s/次）、与真实使用交织、批量采集用 oraclebatch 一次往返 |
| 连续 verbatim 重放 | 重复请求检测（二次即 hit_shark） | 每次变异：新 search_session_id/bcm_chain btm_show_id/时间戳；间隔 ≥30s |
| hook 注入时机 | 触发 metasec 环境检测 | 冷启动完成后再 attach；勿 hook 275064 区 |
| PC 直连被系统代理劫持 | 自签证书失败/误入 Charles | trust_env=False + 本机直连 |

**数据期（正式拿数据的长期策略）**
- 节奏：单关键词 ≤10 次/小时；请求间隔 5-15s 随机（指数抖动）；翻页 ≤5 页/会话；避开整点分钟；dry-streak 跳带（连续 2 页 0 新 → 停 10 分钟）。
- 序列：进入路径仿真：history_words_get → sug → general（首屏）→ refresh_related；翻页同 search_session_id + search_session_round 递增 + pre_search_id_list 携带。
- 会话：cookie 会话生命周期内使用；多身份轮换时保持 device_id/install_id/cookie/八神 同源；pm clear 换身份会丢登录态（游客态可搜索）。
- 参数完整性：body 用全量模板（2283B 参数集），仅替换 keyword/count/cursor/session_id/round/bcm_show_id；头保留全套（含 bd-ticket-guard 抓包值）。
- 设备-IP-账号一致性：PC 出口 IP 与手机不同 → 低频请求下无碍（8/28 实证：全量重放从 PC IP 通过）；避免同 IP 高频多身份。
- 频率预算：单身份 100-200 请求/日；单 IP 500/日；触发 hit_shark 即停 30-60 分钟。
- 监控与止损：响应 NilInfoContext=antispam_check/hit_shark → 熔断 30 分钟；App 显示网络错误 -20013 → 设备已拉黑，pm clear 换身份或等待冷却（≥1h）。

## 五、对抗策略优先级

1. **P0 请求策略**（成本最低、收益最大）：节奏/序列/会话/参数完整性——先行为后算法。
2. **P1 签名+压缩**：八神 RPC oracle + zstd 压缩协议（已具备）。
3. **P2 参数完整性**：全量模板化 body + 真实 cookie（已具备）。
4. **P3 环境检测**：FORGE 证书绕过 + QUIC 降级（已具备）。
止损条件：若 hit_shark 在 ≥5 次间隔 30s+ 的合规节奏下仍持续 → 停采，等待冷却或换身份。

**⚠️ 2026-08-28 终验结论（止损判定）**：
- PC standalone 重放路径 = **死路**（SF-013 同类）：verbatim 重放首次成功，此后同身份所有 PC 请求
  （直连/Charles 转发/现抓现放/冷却 1h 后）均 hit_shark；App 端同身份同出口持续正常。
- 判定：服务端对「设备身份 + 非 App 上下文请求」做关联风控（首次放行采集画像，之后全拒）。
- 止损：**策略 G 在线兜底**——以 App 自身流量为数据通道：
  a) UI 采集：驱动 App 搜索（deep link/UI 自动化）+ uiautomator dump 读渲染结果（标题/作者/点赞，已验证可读）；
  b) 响应 hook：hook App Java 层搜索响应解析（JSON→模型处）截获解密后结果（需定位解析类，产出离线解析器）。

## 六、验证记录

| 日期 | 验证项 | 手段 | 结果 | 证据路径 |
|---|---|---|---|---|
| 2026-08-28 | body 格式判定 | 最小 protobuf body 探测 | invalid_count（格式错误） | scripts/_general_test.py |
| 2026-08-28 | 真实 body 抓取 | Charles 会话导出 entry63/74 | zstd 压缩 form 全参数 | capture/charles_session4,5.json |
| 2026-08-28 | 全量原样重放（E1） | replay_search.py（只换八神） | status=0 无 nil（通过） | 首次重放日志 |
| 2026-08-28 | E1 重复（E2 同字节） | 同 URL/body 二次重放 | hit_shark（重复检测） | replay 二次日志 |
| 2026-08-28 | E3 语义变更 | 新词/新 ts/新 session_id | hit_shark（频控） | dy_search.py 运行日志 |
| 2026-08-28 | 设备拉黑与恢复 | 00:31 枚举→App -20013；pm clear→恢复 | 设备级标记可重置 | ui_dump*.xml |
| 2026-08-28 | 字典 zstd 响应 | template_dict_v1.zstdict 解 app 响应 | Dictionary mismatch（dictID 不同） | 待解 |
| 2026-08-28 | 冷却后重放（1h+） | replay entry74 原样 | hit_shark（身份+上下文关联风控） | replay 日志 |
| 2026-08-28 | 现抓现放 | 触发 App 搜索→立即重放 entry216 | hit_shark | replay --latest 日志 |
| 2026-08-28 | Charles 同上下文重放 | --proxy 127.0.0.1:8888 | hit_shark（栈指纹≠根因） | replay --proxy 日志 |
| 2026-08-28 | App 端对照 | 同身份同出口 App 搜索（面食） | ✅ 持续出结果 | ui_dump6.xml |
| 2026-08-28 | **结论** | PC 重放=SF-013 同类（首次过后续全拒） | **死路（standalone 复刻）→ 策略 G 在线兜底** | 见 §五 |
| 2026-08-28 | 真机参数 oracle | hook38 抓 App 实时构建请求（URL+headers 全新鲜） | ✅ 捕获成功（x-tt-token/guard/trace-id 全新值） | device_main_search.json |
| 2026-08-28 | 真机参数+oracle 八神重放 | device_replay.py（新鲜 headers+模板 body+oracle 八神） | hit_shark（参数新鲜度≠根因） | device_replay 日志 |
| 2026-08-28 | oracle 时钟校验 | X-Khronos vs 真实时间 | 超前 7s（与 App 自身一致，非根因） | oracle 时钟测试 |
| 2026-08-28 | native 字典路线 | libbdzstd 全函数 hook + spawn 启动期抓取 | 无字典/解压事件 → **死路（SF-002 从底层往上）** | hook39 系列日志 |
| 2026-08-28 | **顶层 JSON 通道（SF-002 正解）** | hook org.json.JSONObject/JSONTokener(String) 过滤 | ✅ 448 条搜索 JSON（search_id×380/status×304/result_id×242/author_id×90） | search_json_capture.jsonl |
| 2026-08-28 | JSON 全库覆盖 | org.json+fastjson+gson 全部 parse 入口 | 214 条；主响应(aweme 列表)**不走 Java JSON 层**（native 解析） | search_collect_json.py v2 |
| 2026-08-28 | 响应压缩确认 | 事件 errorExtra | content-encoding=**ttzip**（非 zstd-dict） | 采集事件 JSON |

## 七、泛化经验提炼

本次新增到 general-principles.md 的 E- 条目：E-13（设备级风控可被清数据重置）、E-14（参数完整性=脚本指纹最小化）、E-15（verbatim 重放二次即被重复检测）、E-16（压缩协议缺失→业务侧误判、响应需预训练字典）。

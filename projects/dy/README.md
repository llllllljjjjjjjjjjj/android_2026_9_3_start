# dy.apk 八神接口逆向

## 目标
- APK：`apk/dy.apk`（抖音 com.ss.android.ugc.aweme **38.0.0**，345MB，2026-03 构建）
- 目标：**八神接口** —— 抖音签名体系（x-argus / x-gorgon / x-helios / x-khronos / x-ladon / x-medusa / x-soter，+x-perseus）的生成链路与算法
- 设备：Pixel 4 (9C181EC3BF7E0D)，已升级同版本 38.0.0（签名匹配，数据保留）

## 搜索接口（2026-08-28 新增 ✅ 全链路破解 + 最终结论）

> 详见 `docs/search_api.md`（协议/根因） + `docs/search_collect_usage.md`（采集器用法）。
> 核心结论：
> `POST search5-search-m-hj.amemv.com/aweme/v2/search/general/stream/`
> body = **zstd 压缩的 form-urlencoded**（头 `x-bd-content-encoding: zstd` + `ttzip-version: search_api`），
> 签名 = 八神头在线 oracle（`hooks/dy_hook21.js`，28065c）。
>
> **最终判定（2026-08-28 深夜定稿）**：
> - ✅ 协议层 100% 破解：body / 八神签名 / 动态头 / **zstd 响应字典**（`files/zstd/search_api`，已提取）/ 响应解压全通。
> - ❌ **PC 独立复刻不可行**：hit_shark = **Cronet 网络层指纹风控**（BoringSSL TLS + HTTP/2 帧细节），
>   非参数/签名/字典问题——毫秒级重放（App 现场签名+headers）仍 hit_shark。
> - ✅ **唯一可行采集 = 方向 C（App 代发）**：`scripts/search_collect.py`（搜索走 org.json hook，
>   评论走 oracle 重放），已实测抓搜索+评论成功。
>
> 抓包环境（Charles 中间人链路）SOP 见 `docs/capture-env-setup.md`。

## 电商商品链路（2026-09-01 新增 ✅ 商品接口/产品参数/品牌资质）

> 详见 `docs/ecom_api.md`。核心结论：
> - 商品详情主接口 `POST ecom5-normal-lf.ecombdapi.com/ecom/product/detail/stream/`
>   （body=zstd 压缩表单，八神签名，query 全公共设备参数；完整模板 `capture/detail_stream_req.json`）。
> - **产品参数 = detail/stream 响应内嵌 `attr` 字段**（property_name_all/value 逗号对齐成对，
>   18 属性含注册人/备案人/执行标准/备案文号/产地等），无需独立接口。
> - **产品参数采集（2026-09-02 定稿）**：frida attach 触发 metasec 反检测 App 崩溃 →
>   改**零注入 root 内存 dump**：`scripts/memdump_param.py`（裸跑点开参数弹层 → dump 可读写段
>   → 提取 UTF-16 完整键值串 → 18 项参数），产物 `capture/detail_param_memdump.json`。
> - **品牌资质**：详情页产品信息卡点开参数 → 参数弹层右上「看 >」→ 「资质详情」查看器
>   （页内弹层，图片走图片库缓存）。资质图片本体截屏：`capture/brand_qualification.png`。
> - 商家资质 H5：`haohuo.jinritemai.com/views/shop/multipleLicenses?id=<shop_id>`。
> - 短链 → 302 → `id=<product_id>`（19 位纯数字）；深链 `ec_goods_detail` 已失效（网络异常），改短链打开。
> - 商品搜索接口 `aweme/v2/shop/search/aggregate/shopping/stream/` 会触发语义验证码。
> - PC 独立复刻仍受 Cronet 指纹风控 → App 代发采集（同搜索链路）。

## 现状（2026-08-24，算法还原已完成）

| 项 | 状态 |
|----|------|
| 加壳 | 无（59 个完整 dex，7-10MB/个） |
| 签名核心 | libmetasec_ml.so（= 字节跳动 MS SDK；唯一导出 JNI_OnLoad@0x27e7f0，字符串全加密，反调试导入链） |
| 网络栈 | libsscronet.so（Cronet，sign 头构建函数 0x4127ac → 47A31C → metasec 回调 28065c） |
| **八神结构** | ✅ 全部破解（见 `docs/signature_structure.md`） |
| **X-Argus** | ✅ **完全破解** = base64(LE32(unix_ts))，SF-012 字节级验证 12/12 |
| **X-Khronos** | ✅ = 同源时间戳十进制 |
| **X-Gorgon** | ✅ 结构破解：8404+ctx2B+0001+[4B keyed-hash(query)+14B ctx-token]；输入=query（path/scheme/fragment/headers 排除）；ctx ~0.5s 轮换 |
| **X-Medusa** | ✅ 头部：LE32(内部ts)+~910B 疑似 AES-GCM payload |
| X-Ladon / X-Helios | 部分破解（含签名计数器/ctx 分量；核心在 VMP） |
| X-Neptune | 新发现第 9 头：短 URL 单独输出 |
| **可用交付** | ✅ **在线 oracle**：`hooks/dy_hook21.js` RPC（oracle/oraclebatch）+ `scripts/dy_oracle_collect.py` 采集器（112 组数据在 `capture/oracle_dataset.json`） |
| IDA | 9.2 headless（idat.exe -A -S 批处理可用） |
| frida | f1657 (16.5.7)，客户端 .venv-frida-16.5.7 |

## 关键锚点（本版本实测）

- libsscronet.so 0x4127ac-0x4130bc：签名头名构建函数（x-argus@0x73985, x-khronos@0x74dc4, x-gorgon@0x7a967, x-ladon@0x7a970 的 xref）
- libsscronet.so 0x76247："x-metasec-bypass-ttnet-features"；0x8021d/0x999ee："Tt-Forbid-Reuse"
- libmetasec_ml.so JNI_OnLoad 0x27e7f0

## 目录

```
apk/         原始 APK
decompiled/  jadx 反编译产物（生成中）
hooks/       Frida hook 脚本
scripts/     IDA/Python 分析脚本
so_analysis/ libmetasec_ml.so / libsscronet.so
capture/     抓包产物
artifacts/   IDA 扫描结果 / 日志
docs/        分析笔记
```

## 参考文献

- 看雪《某视频APP七神签名之X-Gorgon生成逻辑逆向分析》https://bbs.kanxue.com/thread-291170.htm
- 52pojie 同文 https://www.52pojie.cn/thread-2107248-1-1.html
- GitHub douyin-seven-signatures-index https://github.com/sanye891/douyin-seven-signatures-index

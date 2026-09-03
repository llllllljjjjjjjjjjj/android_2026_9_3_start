# 抖音商城商品链路逆向 — 商品接口 / 产品参数 / 品牌资质

> 目标：`【抖音商城】https://v.douyin.com/<短链> 商品名` 分享消息形式的数据采集。
> 链路：短链 → 商品详情接口 → 产品参数（详情响应内嵌）→ 品牌资质图片。
> 环境：抖音 38.0.0（com.ss.android.ugc.aweme）/ Pixel 4 / Android 10 / florida-server 16.5.9。
> 样本商品：溪木源层孔菌精华水 230ml，product_id=`3770115268144136255`。

## 0. 短链解析

`v.douyin.com/<code>` → 302 → `haohuo.jinritemai.com/ecommerce/trade/detail/index.html?...&id=<product_id>&...`。
`id` = `product_id`（19 位纯数字）。PC 直接 `curl -I` 即可，无需签名。

## 1. 接口清单（App 内电商链路实测）

| 接口 | 方法 | 用途 |
|------|------|------|
| `https://ecom5-normal-lf.ecombdapi.com/ecom/product/detail/stream/` | POST | ★商品详情主接口（参数/资质/图文全在这） |
| `https://ecom5-normal-lf.ecombdapi.com/ecom/product/detail/preload` | GET/POST | 详情预加载 |
| `https://ecom5-normal-lf.ecombdapi.com/ecom/product/detail/pack/async` | POST | 异步包（推荐流等，`target_id`=`product_id`） |
| `https://ecom5-normal-lf.ecombdapi.com/aweme/v2/shop/promotion/pack/` | POST | 促销信息 |
| `https://ecom5-normal-lf.ecombdapi.com/aweme/v2/shop/user/behavior/` | POST | 用户行为上报 |
| `https://ecom5-normal-lf.ecombdapi.com/aweme/v2/commerce/bff/homepage` | POST | 商城首页 |
| `https://ecom5-normal-lf.ecombdapi.com/aweme/v2/shop/search/aggregate/shopping/stream/` | POST | 商品搜索（触发语义验证码，慎用） |
| `https://ecom5-normal-lf.ecombdapi.com/aweme/v2/commerce/bff/homepage/favorite/feed` | POST | 商城商品信息流 |

商家资质 H5（详情页「商家资质」入口）：
`https://haohuo.jinritemai.com/views/shop/multipleLicenses?id=<shop_id>`（`shop_id` 在 detail 响应里）。

## 2. 请求形态（与搜索接口同构）

### 2.1 detail/stream 完整请求模板（实测抓取，见 `capture/detail_stream_req.json`）

```
POST https://ecom5-normal-lf.ecombdapi.com/ecom/product/detail/stream/
query（全为公共设备参数，product_id 不在 URL）:
  klink_egdi=<会话级> & iid=305014557150939 & device_id=2310516478094584 & ac=wifi
  & channel=huawei_1128_64 & aid=1128 & app_name=aweme & version_code=380000
  & version_name=38.0.0 & device_platform=android & os=android & ssmix=a
  & device_type=Pixel+4 & device_brand=google & language=zh & os_api=29 & os_version=10
  & manifest_version_code=380001 & resolution=1080*2236 & dpi=440
  & update_version_code=38009900 & _rticket=<毫秒> & package=com.ss.android.ugc.aweme
  & first_launch_timestamp=<首启秒> & last_deeplink_update_version_code=38009900
  & cpu_support64=true & host_abi=arm64-v8a & is_guest_mode=0 & app_type=normal
  & minor_status=0 & appTheme=light & is_preinstall=0 & need_personal_recommend=1
  & is_android_pad=0 & is_android_fold=0 & ts=<秒> & cdid=<uuid>

body: zstd 压缩的 x-www-form-urlencoded（头 x-bd-content-encoding: zstd，
  content-length≈2651；product_id/shop_id/session_id 等业务参数在 body 内）

关键头:
  content-type: application/x-www-form-urlencoded; charset=UTF-8
  x-bd-content-encoding: zstd          ← body 是 zstd 压缩表单
  ttzip-version: 444300 / ttzip-tlb: 1 / accept-encoding: gzip, deflate, br, ttzip
  x-ss-stub: 40C5C61230D0C3AB6BD4DB1109DD5D37   ← 会话内固定（MD5(61KB 上下文)）
  x-tt-request-tag: s=0;p=0 / x-ss-dp: 1128 / x-tt-trace-id / x-tt-dt
  compressed-bcm-chain（gzip+b64）/ x-bd-client-key / bd-ticket-guard-* 全家桶
  cookie: 登录态全家桶（sessionid/sessionid_ss/passport_csrf_token/d_ticket/odin_tt/...）
  user-agent: com.ss.android.ugc.aweme/380001 (Linux; U; Android 10; zh_CN_#Hans; Pixel 4;
              Build/QQ3A.200605.001; Cronet/TTNetVersion:6f1e308d 2025-12-08 ...)
  + 八神头（x-argus/x-gorgon/x-khronos/x-ladon/x-medusa/x-helios）
    —— 由 libmetasec_ml.so+0x28065c 在线追加（oracle: hooks/dy_hook21.js）
```

## 3. 产品参数（无需独立接口）

**产品参数 = detail/stream 响应内嵌字段**，弹层为本地渲染。实测字段结构：

```json
"attr_id": "716,1679,1687,4136,...",
"property_name_all": "适用人群,包装类型,品牌,注册人/备案人的名称,产品执行的标准编号,主成分,是否临期,产品净含量,适合肤质,适用季节,功效,是否为特殊用途化妆品,产地,备案/批准文号,规格类型,生产企业名称,产品名称,保质期",
"value": "普通人群,普通装,溪木源,诺德溯源（广州）生物科技有限公司,粤G妆网备字2022112425,层孔菌提取物,否,120ml,混合性肤质,四季通用,舒缓肌肤|保湿|控油,否,中国大陆,粤G妆网备字2022112425,正装,诺德溯源（广州）生物科技有限公司,溪木源层孔菌组合,3年"
```

`property_name_all` 与 `value` 逗号对齐成对。19 个属性涵盖注册人/备案人、执行标准编号、
备案/批准文号、产地（香港品牌此处为「中国香港」）等全部产品参数。

证据文件：`capture/memscan_json/json_008.txt`（detail/stream 响应内存片段）。

## 4. 品牌资质

### 4.1 页面链路（App 内）

详情页「商品」tab 下滚到产品信息卡 → 点击「适用人群」行 → 弹出产品参数半屏（注册人/备案人、
执行标准编号、主成分、是否临期…）→ 右上「看 >」→ 打开「资质详情」图片查看器（1/1 图）。

### 4.2 资质详情来源（2026-09-02 修正 ✅）

- 产品参数弹层 = Lynx 模板 `ecommerce_extensions_aweme/extensions/property_panel/template.js`；
  弹层内「已获品牌官方授权」标记 → 点击打开「资质详情」图片面板。
- 资质图片面板 = Lynx 模板 `fe_reactlynx_ecommerce_images_show_panel/template.js`
  （公网 CDN：`lf-webcast-sourcecdn-tos.bytegecko.com`，通过 `cal_jsb_auth` bridge 认证）。
- 图片数据（ECUrlModel 列表）由 App 原生通过 Lynx props 传入，**无独立业务接口**；
  「返回图片接口」本质是图片 CDN 直链 HTTP GET。
- 资质图片 = **商家证照公示图**，URL 结构（已破解，可直链下载）：
  `http://pXX-item.ecombdimg.com/img/tos-cn-i-6vegkygxbk/<hash>~tplv-5mmsx3fupr-water:<base64水印>:686:970.jpeg`
  水印 base64 `5Lqu54Wn5YWs56S65LiT55So5aSN5Y2w5peg5pWI` = 「**亮照公示专用复印无效**」。
  实测 `p26/p3-item.ecombdimg.com` 直链 HTTP 200 + image/jpeg。
- 资质图片 key 从内存 dump 提取：锚点 `tos-cn-i-6vegkygxbk/`（UTF-8）或 `title:资质详情`
  callback JSON（`{"images":[{"uri":"...","url_list":[...]}],"title":"资质详情"}`）。
  脚本：`scripts/search_img_url.py` / `scripts/search_hash_ctx.py`，证据 `capture/auth_img_urls.txt`。

### 4.3 图片域名抓包（已验证的 skill SOP）

图片域名（douyinpic/ecombdimg/byteimg/bytednsdoc 等）同样走字节魔改 BoringSSL custom_verify
（语义反转），Charles/mitmproxy 证书默认被拒。绕过 = FORGE hook（`hooks/dy_hook30_img.js`，
原生 API_RE 扩展图片域名版）+ spawn 注入 + 图片域名分流到 mitmproxy：

```
1) iptables -I OUTPUT 1 -p udp --dport 443 -j REJECT   # QUIC 降级 TCP
2) mitmdump -p 8090 -w capture/ecom_pics.flow           # mitmproxy CA 需装入系统信任区
3) Xray ss-in(8388) → 域名分流: API→direct / 图片CDN→127.0.0.1:8090
4) frida spawn 注入 hooks/dy_hook30_img.js              # FORGE 图片域名握手 1→0
5) App 走详情 → 图片请求全部明文落入 flow（已实测 29 条图片 flow，sellpoint/douyinpic 等 HTTP 200）
```

实测结果：15 个图片域名 FORGE 生效、图片流量全部解密。带授权书图的商品在此链路下
授权书会作为网络图片请求被抓（URL + 响应字节）。

## 5. 采集 SOP（每条分享消息）

```
1) PC: curl -I https://v.douyin.com/<code> → 302 Location 取 id=<product_id>（+标题/价格在 goods_detail 参数）
2) 真机 App: am start -a VIEW -d https://v.douyin.com/<code>（短链直接打开，实测可用）
   ⚠️ 深链 snssdk1128://ec_goods_detail?product_id=xxx 已失效（打开显示「网络异常」），改短链
3) 手动滚动到产品信息卡，点开产品参数（弹参数半屏）
4) ★零注入提取（2026-09-02 定稿，唯一稳定路径）：
   python scripts/memdump_param.py
   → root dump App 可读写段 → 搜 UTF-16 完整键串/值串 → 18 项产品参数 key:value
5) 授权书图（如有）：资质详情弹层「看 >」查看器截图
```

### 5.1 零注入 root 内存 dump（反 frida 对抗结论）

**frida attach 会触发抖音 metasec 反检测，App 在 60-90s 后崩溃重启**（多次实测，含纯 attach
无 hook 场景），故详情接口采集改用**零注入**：

- App 裸跑（不挂 frida，不崩）→ 短链打开详情页 → 手动点开产品参数弹层。
- 弹层渲染后，产品参数以 **UTF-16LE 完整逗号串**形式驻留内存（Java String）：
  - 键串：`适用人群,包装类型,品牌,...,保质期`
  - 值串：`普通人群,普通装,溪木源,...,3年`
- `scripts/memdump_param.py`：root 读 `/proc/<pid>/maps` → dd 所有 `rw-p` 段 →
  搜 UTF-16 完整串 → 逗号对齐成 18 项 key:value。
- 产物：`capture/detail_param_memdump.json`（已实测 18/18 项正确，含备案文号/生产企业/产地）。

> 为何内存扫描 property_name_all 失效：detail 响应原始 JSON 在 native 解析后即释放；
> 渲染层字段名是 C++ SSO 常量（非 JSON 文本），值才是 UTF-16 Java String。稳定提取
> 目标是 UTF-16 的**完整逗号串**（键串/值串），不是 JSON 键名。

## 6. 资产清单

| 文件 | 内容 |
|------|------|
| `hooks/dy_hook88_url.js` | 全量 URL 捕获（28065c，轻量 RPC） |
| `hooks/dy_hook89_picscan.js` | 单次内存图片 URL 扫描（RPC picscan） |
| `hooks/dy_hook90_qual.js` | qualification 上下文 JSON + 图片 URL 提取 |
| `hooks/dy_hook93_qualbig.js` | 512KB 大窗口 qualification dump |
| `scripts/ocr_screen.py` / `ocr_crop.py` | 截图 OCR 坐标辅助 |
| `scripts/url_watch.py` / `grab_detail_req.py` / `spawn_grab_stream.py` | 请求抓取器 |
| `scripts/memdump_param.py` | ★零注入 root 内存 dump + 产品参数提取（稳定路径） |
| `scripts/extract_param_final.py` | 从已 dump 的 memdump.bin 提取产品参数 |
| `scripts/detail_param_rpc.py` / `hooks/dy_hook_detail_param.js` | Frida RPC 尝试（attach 触发反检测崩溃，已弃用） |
| `capture/memscan_json/` | detail/stream 响应内存片段（json_008 含完整产品参数） |
| `capture/brand_qualification.png` | ★品牌资质图片本体（查看器截图） |
| `capture/detail_stream_req.json` | detail/stream 完整请求（若 spawn 抓取成功） |
| `capture/ecom_cap.jsonl` | hook86 落盘请求记录（103 条） |
| `capture/pics_baseline.txt` | 详情页内存图片 URL 全集（97 条） |
| `docs/ecom_param_auth_method.md` | ★产品参数 + 资质图片零注入逆向方法（坑清单 + 脚本索引） |

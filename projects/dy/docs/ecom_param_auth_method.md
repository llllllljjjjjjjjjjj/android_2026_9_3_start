# 抖音电商详情：产品参数 + 资质图片 零注入逆向方法（2026-09-02 定稿）

> 目标：拿抖音商品详情页的**产品参数**（attr 18 项）与**「官方品牌授权」资质详情图片**（多张证照公示图）。
> 核心结论：**frida attach 触发 metasec 反检测导致 App 崩溃，唯一稳定路径是零注入 root 内存 dump**。

## 1. 环境与前置

- 抖音 38.0.0（com.ss.android.ugc.aweme）/ Pixel 4 / APatch root / florida-server 16.5.9。
- 短链打开详情页（**深链 `snssdk1128://ec_goods_detail?product_id=` 已失效**，显示「网络异常」）：
  `adb shell am start -a VIEW -d https://v.douyin.com/<code>`
- 产品参数、资质图片数据都在**内存**，不依赖抓包/签名（PC 直发撞 hit_shark）。

## 2. frida attach 崩溃结论（关键止损）

- **frida attach 抖音后，App 在 60–90s 内崩溃重启**（metasec 反检测，含纯 attach 无 hook 场景，多次实测）。
- 因此详情页数据采集**放弃 frida**，改零注入 root dump（App 裸跑不崩，手动触发，dump 内存提取）。
- 产品参数/资质图片数据在触发后驻留内存（Java String 是 UTF-16），dump 时机在触发后即可。

## 3. 零注入 root 内存 dump 方法

### 3.1 只 dump 关键段（快）

接口/图片 URL 在 **dalvik 堆**（UTF-16），产品参数也在 dalvik；native heap(libc_malloc) 只有短命 URL。
所以拿参数/图片要 dump **全部 rw-p 段**（约 1.7GB），只 dump libc_malloc 会漏。

### 3.2 dump 脚本（两个坑已修）

```sh
#!/system/bin/sh
pid=$1; out=/data/local/tmp/dump.bin; : > $out
while read range perms offset rest; do
  case "$perms" in
    rw-p)
      s=${range%-*}; e=${range#*-}          # 坑1: maps 第一列是 start-end，必须拆
      s=$(printf %d 0x$s); e=$(printf %d 0x$e)  # 坑2: $((16#$s)) 在设备 sh 算成 0，用 printf %d 0x
      sz=$((e-s))
      [ $sz -gt 65536 ] && dd if=/proc/$pid/mem bs=4096 skip=$((s/4096)) count=$((sz/4096)) >> $out 2>/dev/null
      ;;
  esac
done < /proc/$pid/maps
```

关键：**Windows 写 sh 必须 `newline="\n"`（LF）**，否则 CRLF 导致设备 sh 语法错误。

## 4. 产品参数提取（18 项 key:value）

- 产品参数在内存是 **UTF-16LE 完整逗号串**，不是 JSON 键名：
  - 键串：`适用人群,包装类型,品牌,...,保质期`
  - 值串：`普通人群,普通装,溪木源,...,3年`
- **锚点 = 完整串前几项**（UTF-16LE 编码）搜：
  `"适用人群,包装类型,品牌".encode("utf-16-le")` / `"普通人群,普通装,溪木源".encode("utf-16-le")`
- 命中的键串尾部有指针残留（韩文乱码），清洗：截断 `\uac00-\ud7af` 韩文区 + 保留中文字母数字 `|/()%`。
- 逗号对齐成对即 18 项参数。脚本：`scripts/memdump_param.py`。

> 为什么搜 `property_name_all` 明文失效：detail 响应原始 JSON 在 native 解析后即释放；
> 渲染层字段名是 C++ SSO 常量（`property_name_all\0` 后面跟指针），值才是 Java UTF-16 String。
> 稳定目标 = UTF-16 的**完整逗号串**。

## 5. 「官方品牌授权」资质图片逆向

### 5.1 页面链路（已确定）

产品参数弹层（Lynx `ecommerce_extensions_aweme/extensions/property_panel/template.js`）
→「已获品牌官方授权」标记 → 打开资质图片面板
（Lynx `fe_reactlynx_ecommerce_images_show_panel/template.js`，
公网 CDN `lf-webcast-sourcecdn-tos.bytegecko.com`，通过 `cal_jsb_auth` bridge 认证）。

### 5.2 图片数据来源（关键判断）

- 点击「官方正品/品牌授权」**零接口请求**（实测只有 app_log 埋点，无 ecombdapi 请求）。
- 资质图片 hash **在打开详情页时就已在内存**（detail 响应加载后 15s 内），
  **不需要点击**（2026-09-02 实测：不点击 dump 拿到的 3 个 hash 与点击后完全一致）。
- 图片数据（ECUrlModel 列表：uri + url_list）由 App 原生通过 Lynx props 传入，
  **无独立业务接口**。「返回图片接口」本质是图片 CDN 直链 HTTP GET。
- PC 直发电商接口（preload/stream）**连接级风控**：TLS 握手后静默挂起超时
  （非 hit_shark JSON，GET/POST 均超时）→ 协议化直发不可行，必须 App 打开详情页一次。

### 5.3 全自动采集（无需点击）

`python scripts/auto_collect.py --code <短链code> --name <商品名>`

流程：短链打开详情页 → 等 15s（hash 已进内存）→ 零注入 dump → 提取 hash → 下载图片。

### 5.3 图片 URL 结构（已破解，可直链下载）

```
http://pXX-item.ecombdimg.com/img/tos-cn-i-6vegkygxbk/<hash>~tplv-5mmsx3fupr-<变体>
```

- 域名：p3/p26-item.ecombdimg.com；桶：tos-cn-i-6vegkygxbk。
- **无水印原图**：`~tplv-5mmsx3fupr-image.jpeg`（原图，134KB 级）
- 水印版：`~tplv-5mmsx3fupr-water:<base64水印>:686:970.jpeg`（45579B，压缩+水印）
  水印 base64 `5Lqu54Wn5YWs56S65LiT55So5aSN5Y2w5peg5pWI` = 「亮照公示专用复印无效」。
- 提取：内存 dump 搜 `~tplv-[a-z0-9]+-water:` 锚点得 hash，换 `-image` 后缀下载无水印版。

### 5.4 提取全部资质图片

- 内存 dump 搜锚点 `~tplv-5mmsx3fupr-water:`（水印公示图特征，正则匹配完整 URL）。
- 去重按 `<hash>`（32 hex）→ 得到该商品全部资质图片（本样本 6 张）。
- 脚本：`scripts/extract_auth_imgs.py`（提取）+ `scripts/download_auth_imgs.py`（下载）。

## 6. 关键坑清单（复用）

1. frida attach 抖音 60–90s 必崩 → 零注入 root dump 是唯一稳定路径。
2. 深链 `ec_goods_detail?product_id=` 已失效 → 改短链 `v.douyin.com/<code>`。
3. 内存扫 `property_name_all` 是 SSO 常量（非 JSON）→ 扫 UTF-16 完整逗号串。
4. maps 第一列是 `start-end`（read 字段错位）；`$((16#hex))` 设备 sh 算 0 → `printf %d 0x`。
5. Windows 写设备 sh 脚本必须 LF（`newline="\n"`）。
6. 接口 URL 短命（请求完释放）→ 抓 URL 要在点击后立即 dump；产品参数/图片 URL（Java String）持久。
7. native heap(libc_malloc) 不含业务接口 URL → 抓接口要 dump 全部 rw-p（含 dalvik）。
8. 资质图片是商家证照公示图（水印「亮照公示专用复印无效」），非品牌授权书。
9. 资质图片数量因商品而异（溪木源 6 / 洗衣机 3 / 奥马 1），打开详情页 15-25s 后 hash 已在内存。
10. 部分商品（如奥马）短链 `am start` 自动跳转显示「网络异常」。
    **根因**：短链跳转走 H5 中转链路（`haohuo.jinritemai.com/ecom/product/detail/h5/sc/` →
    native），detail 请求带 `origin_type=detail_share&is_native_h5=1` 的 H5 上下文，服务端拒绝；
    手动搜索进入走纯 native（无 H5 上下文），正常。`sslocal://` 深链外部 `am start` 打不开
    （H5 内部跳转 scheme，`unable to resolve Intent`）。→ 短链失败时手动搜索进入 + dump。
11. 统一采集脚本 `scripts/collect.py`：短链解析 → 冷启动 → 自动打开 → 网络异常检测 → 手动回退 → dump。

## 7. 脚本清单

| 脚本 | 作用 |
|------|------|
| `scripts/memdump_param.py` | 零注入 dump + 提取产品参数（端到端） |
| `scripts/extract_param_final.py` | 从 dump 提取产品参数（UTF-16 完整串） |
| `scripts/extract_auth_imgs.py` | 提取资质图片全部 URL |
| `scripts/download_auth_imgs.py` | 下载资质图片 |
| `scripts/urldump.py` / `fast_urldump.py` | dump 抓接口/图片 URL |
| `scripts/search_img_url.py` / `search_hash_ctx.py` / `search_field.py` | 内存 dump 分析 |

产物：`capture/detail_param_memdump.json`（18 项参数）、`capture/auth_imgs/*.jpeg`（6 张资质图）。

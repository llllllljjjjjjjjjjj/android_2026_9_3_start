# 签名逆向案例库（全部实战案例详述）

> 本文件由 `SKILL.md 案例速查` 引用，属于**按需加载**层：复用已攻克 APP 的算法形态/策略/坑/产物路径时读。SKILL.md 只保留案例名索引。每个案例标注策略与教训编号（SF-xxx）。

---

## 案例速查

### XHS x-mini-sig
```
算法: GF(2^8) flattened transform + SHA-256 canonical tail
策略: F (op list 提取)
错误: 50+ HMAC 爆破失败
教训: SF-001 — 不要假设是已知加密变种
文件: projects/xhs_apk/analysis/xmini_headers/xmini_sig_pure.py
```

### XHS Shield  
```
算法: 白盒 AES → 变种 MD5 → RC4 变种 → Base64
策略: A (已有开源参考)
跨版本: 稳定 (9.11.0 → 9.18.0 仍可用)
文件: xhs_pure_protocol/shield_ref/shield_sdk.py
```

### Apple Music X-Apple-ActionSignature
```
算法: FairPlay SAP (ECDH + HMAC-SHA256 + AES-CTR)
策略: D (Frida 会话提取, CFF 200+ handler 无法静态还原)
SO: x86_64 (MuMu), ARM64 (真机)
文件: projects/applemusic/x_apple_action_signature/
```

### Bilibili GeeTest w
```
算法: 自定义 Base64 + AES-128-CBC + RSA PKCS1v15
策略: A (标准算法组合)
验证: Python vs Node.js 字节一致
文件: projects/appbilibili/geetest/w_generator.py
```

### ct_client（爱加密/电信）— 多签名族
```
getLoginRandomCode (SMS发码): 明文JSON信封(Retrofit @k7.c 无 @k7.a → isReqEnc=false, 无整体3DES/无签名头)
  + 字段级凯撒+2(仅 phoneNum/androidId)。策略: 抓包+注解判加密层; 别碰天翼{p,k}一键登录SDK弯路。
  验证: 字节级 2/2。文件: projects/ct_client/scripts/ct_getrandomcode.py
滑块发短信 (纯算端到端, 无设备/Frida): 取滑块图→CV解缺口→verificationSliderPicture(g.t)→signSignatureString(服务端下发)→smsId
  g.t(v,extra)=Base64(AES/ECB/PKCS5(v, key=Base64.decode(extra))); 32B key=AES-256
  distance=gap_x/(0.848*bg_w)["ui"模式]; 轨迹"x#y#t"加速S曲线+overshoot。文件: projects/ct_client/scripts/ct_slider.py
loginAuthCipher (userLoginNormal登录体): PT(64B)=各字段右填'$'(0x24)到固定宽拼接(无分隔符)
  → RSA_public_encrypt(PT, strPublicKey1, RSA_PKCS1_PADDING) → 128B → base64(~172字符)
  策略: RSA(明文64B确定→hook RSA_public_encrypt 入参核对; 密文每次随机不可逐字节)。文件: loginAuthCipher_gen.py
e9hgat5k (msec libmsec.so 防爬token): base64url(RSA_blob[260B]) + ".." + base64url(AES_ct[829B]) [+ "." + suffix]
  RSA-1024(E=65537, N=c190b4f5..62137f83, 真机堆dump提取)包裹会话密钥; AES_ct=设备指纹JSON的AES-256密文
  策略: 长度/结构对拍(会话密钥rand+无server私钥)。★ unidbg 错算AES见 SF-014。文件: e9hgat5k_gen.py
```

### 连信（掌信 v8.6.901.1，libzhangxin 梆梆）
```
sendsms 信封加密: Content-CKey=RSA/ECB/PKCS1(16随机小写字母, pub1@0x1860AE 2048bit/e=65537) → 256B → hex(512字符)
  body=AES/ECB/PKCS5(json_utf8, key=同那16字节CKey直接当key); 头 Content-CKey-Version=12, Content-Encrypted-ZX=1
  ★坑: org.json.JSONObject.toString() 把 '/' 转义 '\/'(python json.dumps 不转); 字段真实顺序+hashKey末尾+紧凑无空格
  hashKey=固定常量MD5(疑APK完整性, 与body无关)。策略: C(梆梆内存dump脱壳, 见 android-unpack)+静态
  验证: 全链路Frida-oracle字节级一致。文件: projects/lianxin_apk/src/lx_crypto.py
```

### 淘宝闪购 / me.ele MTOP（★生命周期绑定止损案例）
```
签名输入(已全还原): data="<appkey>"&md5hex_lower(body|query)&t → IUnifiedSecurityComponent.getSecurityFactors(...)
  → {x-sign,x-mini-wua,x-sgext,x-umt}(URLEncoded)。IUnifiedSecurityComponent = 动态代理 $ProxyN(每次号变)
  网关 getSecurityFactors 仅冷启 homefeed 拉取触发; spawn 模式 Java.perform 回调不执行(Atlas延迟)
策略: ★G 在线兜底 —— verbatim重放App原签名=SUCCESS, 旁路/真机SG重签=FAIL_SYS_ILEGEL_SIGN(绑会话序列, SF-013)
  纯离线不可行 → hook libxquic 抓App合法签名流量 → 解析。文件: projects/taobao_shangou/{mtop_capture.js,collect_live.py}
魔改frida-server进程名乱码: 按名 attach 失败 → 用 enumerate_applications().identifier=="me.ele" 取 pid
```

### 抖音 38.0.0 八神签名（libmetasec_ml.so = 字节跳动 MS SDK，★VMP+轮换密钥案例）
```
入口: libsscronet 47A31C → metasec+0x28065c 回调 char*(url,headers)→"name\r\nvalue\r\n..." 串
  (内部: 264E3C 签名主函数(加密函数指针) → 274C60 VMP interp(⚠️275064区 syscall包装+0x312768B checksum反hook勿hook) → 2810d4 dispatcher)
八神结构(112组RPC差分+SF-012字节级验证):
  X-Argus  = base64(LE32(unix_ts))  ★完全破解, 12/12跨秒+8/8历史全吻合
  X-Khronos = 同源 ts 十进制 (metasec 内部缓存时钟, RPC 空闲期间按批推进)
  X-Gorgon = 8404 + ctx2B(高位偶数化) + 0001 + [4B keyed-hash(query) + 1B ctx + 13B ctx-token]
    ★输入=query字符串 (path/scheme/fragment/headers 全部排除; 与静态 strchr('?'/'#') 提取器互证)
    ★ctx ~0.5-0.6s 轮换(App后台活动驱动) → 离线不可复现; 4B≠md5/crc32=keyed hash
  X-Medusa = LE32(内部ts) + ~910B 疑似 AES-GCM payload(尾16B tag)
  X-Ladon  = 4B (第4字节=ctx线性分量, 第3字节含签名计数器奇偶交替)
  X-Helios = 36B 全输入敏感; X-Neptune=短URL单独输出(-8|...最小签名)
策略: ★H 在线 oracle (VMP核心+轮换密钥 → 纯算死路) — App运行 + Frida RPC 直调 28065c 即签名服务
坑: ① App 运行后从 frida 进程表反枚举消失 → adb pidof 直连 attach(pid)
    ② frida 16.5.7 RPC 方法名必须全小写(Python绑定 lower() 查找, camelCase 报 unable to find method)
    ③ 空 url RPC 返回 NULL 不崩; RPC 线程上 Khronos 滞后真实时间
文件: projects/dy/{hooks/dy_hook21.js,scripts/dy_oracle_collect.py,capture/oracle_dataset.json,docs/signature_structure.md}

★oracle 重放改造边界（2026-08-27 评论接口 /aweme/v2/comment/list/ 实证, 见 SF-018/019）
  ① body 语义绑定: session_show_cids 与客户端会话状态绑定校验(改真/假 cid 均 -99999)
     zstd 重压缩同语义无碍 → body 只可字节级原样, 要改从 query 改
  ② query 自由: cursor/count 可改 + oracle 重签照过(翻页 B 模式); count 服务器 cap ~50; 其余参数照抄模板
  ③ ★minimal query 换视频: 7 个视频专属参数(aweme_author/authentication_token/top_query_word/
     common_flags/current_l1_comment_count/comment_count/is_fold_list)全砍 + 只改 aweme_id → 照签照回
     (status=0 已验证; 返回评论归属以实跑第1页 [归属] 行确认为准)
  ④ 响应解析: hex 前缀("\xa8"等) + \n\n + JSON → find(b"{") + raw_decode;
     accept-encoding 必须 gzip, deflate, br(不声明 ttzip, 否则响应是 ttzip 需手动解)
  ⑤ IPv4 强制: PC DNS 把 api5-core-lf.amemv.com 解析到 IPv6 直连挂起 → socket.getaddrinfo monkey-patch 只留 IPv4（滤掉 IPv6）
  ⑥ 签名引擎 vs 服务端两层: 简化 URL(砍 query 参数) oracle 返回 X-Neptune -8 最小签名分支(不是八神)
     但含完整 query 的任意 URL 都能签 → 服务端对砍掉的业务参数不校验(两层分开验证, SF-019)
文件: projects/dy/scripts/comment_replay.py (--aweme-id 换视频 / --from-charles 抓模板 / paging B 模式)
     projects/dy/docs/comment_replay_usage.md (换视频两方法 + 翻页机制表 + 已知限制)
```

### 瑞幸 q/sign + 同盾 blackBox
```
q/sign (liblka-secure，干净导出非加壳):
  getKey4LK = AES128-ECB(urlsafe-b64(rawSecret), key="Safe_box_1234567")
  派生 key = NxtPlpL70ssMD8is
  q = b64url(AES128-ECB-PKCS7(paramsJSON, key16))  // ECB→q 前缀恒定
  sign = concat(abs(int32_BE(md5("cid=;q=;uid="+key)[k:k+4])) for k in 0,4,8,12)
  策略 A。e2e: 新 q/sign → capi.lkcoffee.com order/preview HTTP 200/code=1
  文件: projects/luckin/scripts/lka_gen.py
blackBox (同盾): ★真值=26 字符，不是 3000B blob（那是数美）。
  blackBox = LEAD + reverse(td-tid_content)[1:] ，pos 4/15/24 插 3 个 base62
  td-tid 在 shared_prefs/fm_shared.xml；chk 丢弃。策略 A。preview 不校验 blackBox≠过风控
  文件: projects/luckin/scripts/bb_gen.py
教训: 主攻点选对（自研干净 SO）远胜死磕 360 壳/同盾 native
```

### Keeta / 猫眼 mtgsig（美团系）
```
mtgsig = 请求无关设备令牌（非 TEE）：改 body/path 后 a5/a7/a8/a9 不变，仅 a2 变
Keeta Shepherd s-ca-signature = HMAC-SHA256(appSecret, canonical) 纯算通
  纯算 mtgsig 两墙：MD5 白盒 + unidbg 缺 base.apk 资产曾 errno 512（挂裁剪 apk 后可产真令牌）
  传输: Shark 隧道 / libcronet；裸 HTTPS 边缘 403。混合 e2e（离线 body + 设备隧道）code=0
  禁刷无效令牌 → 设备 #41SR 软封（原版 App 也 403）
猫眼: key36[i]=source[i]⊕appKey[i]⊕a10_mask ；source 设备稳定
  a2 纯算 + fp_stack H1 → yanchu project/detail HTTP 200 success（止损：单次只读，勿再刷）
  入口: projects/maoyan/scripts/pure_mtgsig.py + fpstack_client.py
```

### 盒马搜索（止损型）
```
判官: mtop.wdk.search.suggest HTTP 200 SUCCESS + 非空联想
形态: 活机 buildRequestHeaders 全头 + fp_stack H1 verbatim（四头=时效炸弹，非纯算）
入口: projects/freshippo/scripts/search_client.py replay
谱: projects/freshippo/docs/SEARCH_PROTOCOL.md
禁止宣称四头纯算；禁止再刷同一条。search.item / az95 另开
```

### Play login v2 / MinuteMaid DG
```
已解: DG 程序常数 #1/#123/#266 字节级，bytecode=53993
卡点: #2 sealed env（本地 vs live 213 族每块差字段）；MI613e 仍 gf.uicd
形态: 部分解析 + #2 止损。权威 projects/play_login_v2/docs/LOCAL_CLIENT.md
禁止重复无效 POST（同 token 烧号）
```

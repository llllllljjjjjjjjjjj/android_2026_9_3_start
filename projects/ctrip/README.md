# Ctrip 评论/点评接口逆向

逆向携程旅行 App（`ctrip.android.view` 8.85.4）的评论/点评相关接口。

## 现状

- ✅ 反编译完成（jadx，31857 个 java 文件）
- ✅ 网络框架识别：OkHttp + 自研 `CTHTTPClient`（SOA2 网关）+ SOTP/HTTP 管道
- ✅ 点评接口定位（CRN bundle `rn_xtaro_hotelCommentList` + 动态抓包）
- ✅ 签名机制完整逆向（`x-payload-source = libscmain.so native simpleSign(md5(body))`）
- ✅ 签名结论：设备绑定（Android Keystore）+ 会话绑定 → 纯离线不可行
- ✅ 策略 E 落地：Frida RPC 在线签名 oracle（`hooks/sign_rpc.js`，已验证）

## 核心结论

- 点评列表：`POST https://m.ctrip.com/restapi/soa2/24077/h5-json/clientHotelCommentList`
- 酒店点评信息：`POST https://m.ctrip.com/restapi/soa2/34308/getHotelCommentInfo`
- 点评列表是 React Native 模块，接口定义在 CRN bundle 中（不在 DEX 层）

## 文档

- 完整接口文档：[`docs/comment-api.md`](docs/comment-api.md)
- 签名逆向文档：[`docs/signature.md`](docs/signature.md)

## 目录

```
apk/          原始 APK
decompiled/   jadx 反编译产物
hooks/        Frida Hook（capture_review_api.js）
scripts/      扫描/抓包脚本
capture/      点评 bundle + 抓包日志 + 截图
docs/         接口文档
```

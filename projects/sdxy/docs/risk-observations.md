# sdxy 风控观察记录（开关二 YES → [动态] E-/F- 条目）

> 采集期：2026-xx（登录接口在线实证阶段）。来源：`scripts/login_probe.py` / `scripts/captcha_solver.py` / `scripts/probe*.py` 对 `https://api.huachenjie.com/` 的实测。

### [动态] E-cand 登录接口强制图形验证码门槛(1600)
- 类型: 业务规则风控（账号/设备/人机验证）
- 检测原理: 密码登录 `run-front/auth/loginPassword` 与发验证码 `run-front/account/getAuthCode` 在不带任何异常痕迹的情况下稳定返回 `code=1600, message=未执行账户验证`；同一账号 `loginCheck`/`sendRemainTimes` 却正常（code=0）。判定 1600 由服务端风控按「设备/环境/账号」维度的风险评分触发，属人机验证前置。图形验证码为自研 H5 `blockPuzzle`（`mh5.huachenjie.com/run-mobile-web/#/captcha/verify`），接口 `POST /run-front/captcha/get` → `/run-front/captcha/check`。
- 对抗思路: 该验证码为自研滑块（非极验/易盾），`get/check` 均在本 App 同一加密/签名传输层下（需带 `sign`），pointJson 加密 key 来自 App JSBridge `getSecretKey`（`Ukp3hmSe7BmMcgbE`）。可离线复刻 check 协议；但服务端「目标槽位点判定」与拼块来源位置的映射需一次真实成功样本确证后才能全自动过。
- 落地工具: android-recon §3 抓包治理 / android-dynamic §SSL·Hook；签名层复用 `scripts/sdxy_crypto.py`。
- 证据等级: 小样本（单账号单环境多 token 实测；R=1 单设备）
- 置信度: 高（1600 语义与触发点由 VM 分支 + 在线响应双印证）
- 来源: projects/sdxy <登录实测> `scripts/login_probe.py` 输出 + `docs/LOGIN_API.md` §7

### [动态] F-cand 离线密码登录被滑块阻断（未解）
- 触发条件: 纯 PC 模拟端无图形验证码直接调 loginPassword/login_v3 前置 getAuthCode
- 失败特征: 返回 `code=1600`（非账号/密码错误，非 sign 校验失败），登录无法闭环
- 根因分析: 现象——服务端对模拟环境强制人机验证；根因——1600 滑块点判定（槽位坐标）未精确复刻（前端 E 折算式与「来源/槽」映射存在偏差），需真实成功 pointJson 样本校准（真机 Frida hook `checkResult` / 抓包）
- 规避方案: ① 用有效账号在真机完成一次滑块并 Frida hook 捕获 `pointJson` 标定服务端坐标口径；② 或对同 token 采用较窄网格扫描正确 x（注意服务端可能对大量 check 失败有限流，需低频率）；③ 人工传入手机上抓到的 captchaPoint 绕过（把 captchaPoint 作为 client 入参暴露）
- ✅ **已解决（2026-09-07）**：真机 Hook `JavascriptApi.Y`（checkResult）+ `RealInterceptorChain`（同次 getCaptcha 图片 URL）捕获成功样本，标定出**坐标映射**：`x = 图像模板匹配中心 C − 13.5`、`y=15`、`key=Ukp3hmSe7BmMcgbE`（AES-128-ECB-PKCS7-Base64）。`scripts/login_full.py` 已实现全自动滑块 + 密码登录，实测 `code=0` 登录成功（userId=26090400390821949）。
- 影响等级: 严重（拦住密码/短信登录闭环）→ **已降级（已全自动闭环）**
- 证据等级: 已实证（多次实测 1600 + 真机成功样本标定）
- 来源: projects/sdxy <登录实测> `scripts/probe*.py` + `scripts/login_full.py` 输出 + `docs/LOGIN_API.md` §6.2

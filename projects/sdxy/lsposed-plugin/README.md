# sdxy-hook — 阳光跑数据只读记录器（LSPosed 插件）

在**真实跑步场景**下被动记录闪动校园 App 的关键数据，用于补齐静态分析无法还原的
native 未知项：`K.b2s` 图片派生值、`strideMap` 内部 key、`runImgRecord` 精确算法输入、
`signKey/encKey` 实际值、finish body 与检测结果。

> 🔴 **定位**：只读采集，不是伪造、不是发包、不是重放。所有 hook 都不修改参数与返回值，
> App 行为与数据流与未 hook 时完全一致 —— 这是「不被检测」的第一层。

---

## 一、它能补什么（对应静态分析的未知项）

| 未知项 | hook 点 | 记录内容 |
|--------|---------|---------|
| `runImgRecord` 图片派生值 | `com.huachenjie.c.K.b2s(byte[],int)` | 输入像素字节（len+sha256+头32B）+ mode + 输出 String |
| `strideMap` 内部 key | `ApiDataComponent.b0(Map,int,String,ValueCallBack)` | strideList Map 的完整 key/value |
| finish body 精确组装 | `DataComponent.h1(boolean,int)` | 入参 + 返回 Map |
| cheatType→InvalidReason | `DataComponent.L0(int)` | cheatType + 返回 List |
| cheatResult 集合 | `DataComponent.z0()` | 返回 Map |
| `runImgRecord`/`timestamp` 计算 | `mp8.f(Map)` | map 修改前后 |
| `signKey`/`encKey` 实际值 | `c23.d()` / `c23.b()` | 返回值 |
| MD5 输入输出 | `a15.c(String)` | 入参 + 输出 |
| uploadRunRecord body+sign | `qf7.j(List,String)` | pois + runRecordCode |
| stride body | `qf7.l(Map,int,String)` | strideList + strideInterval |
| json→sign | `ParamsInterceptor.getSign(Map)` | 入参 Map + 输出 sign |

拿到这些后，结合静态分析已还原的算法（`sign = AES256-CBC(SHA256(json)旋转, signKey)`、
`runImgRecord = MD5(runRecordCode+"260826158.6.8"+图片值+timestamp)`），即可离线精确复现。

---

## 二、编译

用 **Android Studio**（任意较新版本，自带 JDK，会自动下载 Gradle）打开本目录
`lsposed-plugin/`，直接 Build → Build APK(s)。

产物：`app/build/outputs/apk/debug/app-debug.apk`（或 release）。

> 无 Android Studio 时，用命令行需要本机有 JDK 17 + Android SDK（`local.properties`
> 指定 `sdk.dir`）+ Gradle 8.5+，执行 `gradle assembleDebug`。

---

## 三、部署（反检测三层，缺一不可）

目标真机：Pixel 4（Android 10 arm64，Magisk + Zygisk 已就绪）。

### 第 0 层 — 前置确认

1. Magisk 已开启 **Zygisk**。
2. 已安装 **LSPosed（Zygisk 版）**。
3. 已安装 **Shamiko**（Magisk 模块，隐藏 root/Zygisk 特征）。
4. 已安装 **HideMyApplist (HMA)**（LSPosed 模块，隐藏模块列表）。

### 第 1 层 — 安装并启用插件

1. `adb install app-debug.apk`（包名 `com.sdxy.hook`）。
2. 打开 LSPosed → 模块 → 启用 `sdxy-hook` → 作用域勾选 `com.huachenjie.shandong_school`。
3. 重启手机（LSPosed 要求）。

### 第 2 层 — HideMyApplist 隐藏

1. HMA 新建/选一个模板，勾选隐藏：
   - `com.sdxy.hook`（本插件）
   - LSPosed 管理器、Shamiko、Magisk 管理器、其他逆向工具 App
2. 把该模板应用到 `com.huachenjie.shandong_school`（黑名单或白名单模式）。
3. Shamiko 里把 `com.huachenjie.shandong_school` 加入 **denylist**（Shamiko 用 denylist 隐藏 root/Zygisk）。

### 第 3 层 — 只读 + 真实数据（核心）

- 插件**只读**：不改参数、不改返回值、不改 App 行为。数据 100% 真实自洽。
- **真人真实跑步**：不伪造轨迹、不模拟 GPS、不用 mock 定位（`cheatType 110` 虚拟定位检测
  会命中 `service_mock_location`/`service_fl_ml`）、不注入步数。
- 跑步前**不要**手动调任何接口、不要异常结束、不要残留未完成跑步（这是此前封号的根因）。

---

## 四、采集流程（真实跑步）

1. 重启手机 → 确认 LSPosed/Shamiko/HMA 生效。
2. 打开闪动校园 → 首页 → 运动 → 阳光跑 → 正常开始跑步。
3. **按学校规则真实跑完**（距离/配速/步频/打卡点全部合规）。
4. 正常结束跑步（finishSunRun_v2）。
5. 结束 App 后取日志：

```powershell
adb pull /sdcard/Android/data/com.huachenjie.shandong_school/files/hook/ ./capture/hook/
```

日志文件名 `trace_<pid>.log`，内含所有 hook 记录。

---

## 五、探针先行（防封号的关键步骤）

> 🔴 当前账号已封禁，**务必用新账号 + 新设备**做采集。

在正式跑步采集前，先做一次**无害探针**，确认 hook 不被易盾/风控检测：

1. 安装并启用插件（作用域勾选目标 App）。
2. 打开 App，**只浏览首页/运动页，不开始跑步、不调任何接口**，停留 1~2 分钟。
3. 观察：
   - App 是否正常（不闪退、不弹"环境异常"、能正常加载数据）。
   - 退出后再登录是否正常。
4. 若探针通过 → 再开始真实跑步采集。
5. 若探针异常（闪退/封号提示/环境检测）→ **立即停用插件**，说明易盾检测到了 Xposed，
   转用 §七 的替代方案（Frida native hook / ZygiskFrida）。

> 判断依据：App 本身对 Xposed 的检测强度未知。易盾加固 + 自有风控的组合，
> 存在检测 Xposed 的可能。探针是「不被检测」的最后一道验证，先探针后跑步。

---

## 六、日志分析方法

拿到日志后，对照静态分析结论交叉验证：

1. **`K.b2s OUT`** → 即 `runImgRecord` 的图片派生值（signKey 的图片派生值在静态分析中已
   确认走 `bg_contact_list` XML fallback，这里重点是 `hcj_bg_run_index` PNG 的真实 b2s 输出）。
2. **`c23.d()`** → 确认 `signKey` 是否 = `F44B0282BEA83557`（验证 fallback 结论）。
3. **`ApiDataComponent.b0 strideList=...`** → 看 Map 的 key，补齐 `strideMap` 内部 key。
4. **`getSign IN=... OUT=...`** → 用 `scripts/sdxy_crypto.py` 复算 sign，字节级对齐验证算法。
5. **`mp8.f OUT`** → 看 `runImgRecord`/`timestamp` 的最终值，反推图片派生值 = MD5 的中间项。

---

## 七、若 LSPosed 被检测（替代方案）

易盾若检测 Xposed，按 android-dynamic 技能 §3 的阶梯降级：

1. **Frida native hook**：`Interceptor.attach` 到 `libNetHTProtect.so` 中 `K.b2s` 对应的
   JNI 函数指针（需先在 JNI_OnLoad 的 RegisterNatives 表里定位函数地址）。
2. **ZygiskFrida**（zygote 注入 gadget，不走 ptrace，规避启动期 watchdog）。
3. **ecapture / root 内存 dump 零注入**：不注入，直接在真实跑步时 dump 进程内存，静态扫
   K.b2s 的输入输出串（VMP 下输入输出仍在 Java 层对象里）。

具体操作见 `.dsh/skills/android-dynamic/SKILL.md` §3。

---

## 八、产物索引

| 文件 | 作用 |
|------|------|
| `app/src/main/java/com/sdxy/hook/MainHook.java` | 入口 + 全部 hook |
| `app/src/main/java/com/sdxy/hook/LogUtil.java` | 落盘日志 |
| `app/src/main/assets/xposed_init` | LSPosed 入口声明 |
| `app/src/main/AndroidManifest.xml` | xposedmodule 声明 + 作用域 |

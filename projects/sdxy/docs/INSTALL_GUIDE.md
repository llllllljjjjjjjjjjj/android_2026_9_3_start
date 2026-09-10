# 插件安装与使用指南（最小风险版）

> 插件是 **LSPosed 模块**，没有界面、没有图标入口。安装后它只是一个"空壳 App"（应用名显示为
> **「系统组件」**），真正功能是在「闪动校园」启动时**自动注入 hook 并后台记录日志**。
> 你**不需要打开插件**，只需要正常打开闪动校园跑步即可。

---

## 一、安装 APK

APK 位置：`projects/sdxy/artifacts/sdxy-hook-debug.apk`（15 KB）

**方法 A：电脑 adb 安装（推荐）**
```powershell
adb install D:\reserve_agent\android\projects\sdxy\artifacts\sdxy-hook-debug.apk
```

**方法 B：手机直接安装**
1. 把 APK 传到手机（`adb push ... /sdcard/Download/` 或微信/QQ 传输）。
2. 用 MT 管理器 / 系统文件管理器点击安装。
3. 桌面可能多一个 **「系统组件」** 图标——**不用点它**（点了是空白页，正常）。

---

## 二、在 LSPosed 里启用模块（关键一步）

1. 打开 **LSPosed**（桌面图标；或拨号输入 `*#*#5776733#*#*` 进入）。
2. 点底部 **「模块」** 标签。
3. 列表里找到 **「系统组件」**（包名 `com.app.compat`），点进去。
4. 打开 **「启用模块」** 开关。
5. 在 **「作用域」** 里勾选 **「闪动校园」**（`com.huachenjie.shandong_school`）。
6. 返回。顶部会提示 **「需要重启」**。

---

## 三、重启手机（必须）

LSPosed 模块启用后，**必须重启手机**才会注入到目标 App。重启后插件自动生效。

---

## 四、（推荐）反检测配置

如果已装 Shamiko / HideMyApplist，做以下两项，降低被检测概率：

1. **Shamiko**：把 `闪动校园` 加入 denylist（隐藏 root/Zygisk）。
2. **HideMyApplist**：新建模板隐藏 `系统组件`（com.app.compat）、LSPosed、Magisk 管理器，应用到 `闪动校园`。

> 未装这两个也没关系——插件是**只读 hook**（不改数据、不改行为），数据真实，风险已最低。

---

## 五、探针验证（跑步前必做，防封号）

先做一次无害验证，确认 hook 不被检测：

1. 重启后打开 **闪动校园**。
2. **只浏览首页/运动页，不开始跑步、不点任何提交按钮**，停留 1~2 分钟。
3. 观察：App 是否正常（不闪退、不弹"环境异常"、能正常加载数据）。
4. 检查日志是否生成：

**方法 A（电脑）**：
```powershell
adb shell ls /sdcard/Android/data/com.huachenjie.shandong_school/files/hook/
adb pull /sdcard/Android/data/com.huachenjie.shandong_school/files/hook/ ./hook_logs/
```

**方法 B（手机 MT 管理器）**：
路径 `/sdcard/Android/data/com.huachenjie.shandong_school/files/hook/`
看有没有 `trace_<数字>.log` 文件。

5. **日志内容判读**（最小风险版只 hook 3 个方法）：
   - 有 `session start` → 日志初始化成功。
   - 有 `HOOKED com.huachenjie.c.K.b2s` → 图片值 hook 成功（最关键）。
   - 有 `HOOKED com.huachenjie.running.service.ApiDataComponent.b0` → strideMap hook 成功。
   - 有 `HOOKED com.huachenjie.running.service.DataComponent.h1` → finish body hook 成功。
   - 若日志文件不存在或为空 → 插件没生效，回 §二 检查 LSPosed 是否启用 + 是否重启。

> 探针通过（App 正常 + 日志有 HOOKED）→ 再开始真实跑步。

---

## 六、跑步采集（你只需要正常跑步）

1. 打开闪动校园 → 首页 → 运动 → 阳光跑。
2. **按学校规则真实跑完**（距离/配速/步频/打卡点全部合规，不用任何模拟定位）。
3. 正常点"结束跑步"。
4. 插件在后台自动记录 3 个关键数据（无需你操作）：

| 日志关键字 | 记录内容 | 补全的未知项 |
|-----------|---------|-------------|
| `K.b2s IN ... OUT ...` | 图片像素 sha256 + **输出图片值** | `runImgRecord` 图片派生值 |
| `ApiDataComponent.b0 strideList=...` | **strideList 的 key/value** | `strideMap` 内部 key |
| `DataComponent.h1 OUT=...` | finish body 完整字段 | finish 组装交叉验证 |

---

## 七、取回日志分析

跑完后：
```powershell
adb pull /sdcard/Android/data/com.huachenjie.shandong_school/files/hook/ ./capture/hook/
```

把日志发回给我，我对照静态分析补全最后 2 个未知项（K.b2s 图片值、strideMap key）。

---

## 常见问题

| 问题 | 解决 |
|------|------|
| 日志文件不存在 | LSPosed 没启用模块 / 没勾选作用域 / 没重启手机 |
| LSPosed 列表里找不到"系统组件" | 确认 APK 已安装；模块列表按应用名显示，找「系统组件」不是「sdxy-hook」 |
| 日志只有 session start，没有 HOOKED | 正常——最小版只在进跑步页/开始跑步后才 hook，进跑步页后应出现 |
| App 闪退/弹环境异常 | 易盾检测到 Xposed → 停用模块，改用 Frida 方案 |
| 桌面「系统组件」图标点了是白屏 | 正常，插件无 UI，不用点 |

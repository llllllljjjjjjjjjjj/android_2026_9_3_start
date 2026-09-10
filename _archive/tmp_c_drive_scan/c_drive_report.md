# C 盘目录扫描说明（lenovo / Win11）

- 扫描时间：本次会话
- 容量：C 盘共约 300 GB，已用 237.9 GB，剩余 62.1 GB
- 扫描方式：目录递归（系统目录仅列到 2 层，非系统目录最深 6 层），32 位哈希等无意义缓存目录已折叠
- 主要用户：`C:\Users\lenovo`

---

## 一、C:\ 顶层总览

| 目录/文件 | 类型 | 说明 |
|---|---|---|
| `Windows` | 系统 | 操作系统核心（见下）
| `Program Files` / `Program Files (x86)` | 系统 | 已安装软件（64/32 位，见下）
| `ProgramData` | 系统 | 软件共享配置与缓存数据
| `Users` | 系统 | 用户配置文件与个人数据
| `Recovery` | 系统 | 系统恢复环境（WinRE）
| `System Volume Information` | 系统 | 系统还原点/卷影/VSS 元数据（受保护，勿动）
| `$Recycle.Bin` | 系统 | 回收站（按 SID 分用户）
| `$SysReset` | 系统 | 系统重置/刷新产生的日志
| `Documents and Settings` | 系统 | 旧版兼容链接（junction，指向 Users）
| `pagefile.sys` | 系统文件 | 虚拟内存页面文件，12.5 GB
| `hiberfil.sys` | 系统文件 | 休眠映像文件，9.5 GB（已休眠过）
| `swapfile.sys` | 系统文件 | UWP 应用交换文件，16 MB
| `DumpStack.log` | 系统文件 | 崩溃转储诊断日志
| `appverifui.dll` / `vfcompat.dll` | 系统文件 | 应用验证工具残留 DLL
| `logUploaderSettings*.ini` | 系统文件 | 遥测上传配置

### 用户态顶层目录

| 目录 | 说明 |
|---|---|
| `.ADSPOWER_GLOBAL` | AdsPower 指纹浏览器的全局数据：`.browser`（内置 Chromium 内核）、`cache`（含浏览器 profile `k1cwgby9_i6tfmn`）、`extension`（扩展 id 目录）、`RPA`/`rpa_log`/`screenshot`（RPA 自动化记录与截图）、`components`/`data`（组件与运行数据）
| `KuaiwanGames` | 快玩游戏盒：`Games`（已装游戏）、`Patch`（更新补丁）、`usergame.xml` 记录
| `KuGou` | 酷狗音乐残留：`Lyric`（歌词）、`Temp\tp2p`（P2P 缓存，大量哈希文件，可清）
| `temp` | 临时调试目录：`chrome-debug-profile`（Playwright/调试用 Chrome profile，含浏览器缓存）
| `Solution1` | 一个残留的空 Visual Studio 解决方案（`.vs` + `.sln`，无实际代码）
| `inetpub` | IIS 默认目录，基本空，属系统组件
| `AppData`（根级） | 反常但仅含 `Flash Player` 遗留配置
| `common_attachment` | 某客户端的剪贴板/脚本附件缓存 JSON
| `腾讯应用宝文件管理` | 腾讯应用宝"文件管理"映射目录：电影/图库/图片/文档/下载/音乐等（多为空结构）
| `GameDownload` | 空占位目录
| `leidian` | 空占位目录（雷电模拟器本体数据实际在 Documents/AppData）
| `mingw64` | 空占位目录（MinGW 工具链痕迹）
| `软件下载` | 空目录
| `智迅微信文件备份` | 空目录（微信备份工具残留）

---

## 二、C:\Windows 一层（系统内部，仅标注用途）

| 主要目录 | 用途 |
|---|---|
| `System32` / `SysWOW64` | 64/32 位系统核心 DLL 与可执行文件 |
| `WinSxS` | 组件库（Windows 组件存储，勿手动清理） |
| `assembly` / `Microsoft.NET` | .NET 程序集 / .NET 运行库 |
| `Fonts` | 系统字体 |
| `Boot` | 启动管理器与引导数据 |
| `Installer` | MSI 安装缓存（勿删） |
| `SoftwareDistribution` / `WUModels` | Windows Update 下载与暂存 |
| `Logs` / `debug` / `Minidump` / `LiveKernelReports` / `Panther` | 系统/安装/蓝屏转储日志 |
| `prefetch` | 程序预读取缓存（可清） |
| `Temp` / `SystemTemp` / `CbsTemp` / `TempInst` | 临时文件（可清） |
| `Tasks` / `Servicing` / `Setup` | 计划任务 / 组件服务 / 系统安装 |
| `Security` / `SecureBoot` | 安全策略与安全启动 |
| `Web` | IIS/Web 组件 |
| `IME` / `InputMethod` | 输入法组件 |
| `Speech` / `Speech_OneCore` | 语音识别组件 |
| `WinSxS` 等其余 | 其余均为系统内部目录，仅需知晓存在即可 |
| `Lenovo` | 联想 OEM 系统组件 |

---

## 三、Program Files（64 位软件）

| 目录 | 对应软件/用途 |
|---|---|
| `7-Zip` | 压缩解压工具 |
| `Google` | Chrome 浏览器组件 |
| `NVIDIA Corporation` | NVIDIA 显卡驱动组件 |
| `Intel` | Intel 芯片组驱动组件 |
| `Java` | Oracle Java 运行库 |
| `JetBrains` | JetBrains IDE（PyCharm/IDEA 等） |
| `Microsoft Office` / `Microsoft Office 15` / `OfficePLUS` | Office 套件与增值组件 |
| `Microsoft OneDrive` | OneDrive 网盘客户端 |
| `Microsoft Visual Studio` | Visual Studio 开发环境 |
| `dotnet` | .NET SDK/运行时 |
| `Npcap` | 抓包底层驱动（Wireshark 依赖） |
| `PremiumSoft` | Navicat 数据库管理工具 |
| `Huorong` | 火绒安全软件 |
| `Oray` | 向日葵远程控制 |
| `EVPlayer` | EV 加密视频播放器 |
| `iTop Screen Recorder` | iTop 录屏软件 |
| `Rockstar Games` | R 星游戏平台（GTA 等） |
| `Tencent` | 腾讯软件共享组件 |
| `Lenovo` | 联想自带工具组件 |
| `TechChangeLife` | 三方工具发行商标识目录 |
| `Common Files` / `WindowsApps` / `ModifiableWindowsApps` | 共享组件 / 商店应用 |
| `WSL` | Linux 子系统发行版数据 |
| `Application Verifier` | Windows 应用验证工具（调试用） |
| `Internet Explorer` 等 | 系统内置应用，仅标目录 |

---

## 四、Program Files (x86)（32 位软件）

| 目录 | 对应软件/用途 |
|---|---|
| `Kuaiwan` | 快玩游戏盒 |
| `WXWork` | 企业微信 |
| `VMware` | VMware Workstation 虚拟机 |
| `Google` | Chrome 更新/组件（x86 部分） |
| `Tencent` | 腾讯共享组件 |
| `Microsoft` / `Microsoft.NET` / `Microsoft SDKs` / `Reference Assemblies` | .NET 与 SDK 组件 |
| `Windows Kits` | Windows 调试/驱动开发工具包 |
| `NVIDIA Corporation` | 显卡组件（x86） |
| `Deep Uninstaller` | 强力卸载工具 |
| `Ultra Shredder` | 文件粉碎工具 |
| `PicSnapX` | 截图工具 |
| `MultiTabExplorer` | 多标签资源管理器 |
| `PrivacyGuard+` | 隐私保护工具 |
| `GPU Optimization` | 显卡优化工具（联想系） |
| `LdsDllRepair` / `LdsSysClean` / `LhpMaxProtect` / `LxWallpaper` / `WinAuthority` / `ZxVxTidy` | 装机工具全家桶组件（DLL 修复/系统清理/主页保护/壁纸等，多为推广装机软件，可整体卸载） |
| `Lenovo` | 联想组件 |
| `Common Files` / `WindowsApps` 等 | 系统共享，仅标目录 |

---

## 五、ProgramData 主要厂商目录

`Alibaba`（阿里组件）、`A-Volute`（Nahimic 音效）、`Huorong`（火绒）、`Kingsoft`（金山 WPS 系）、`KuaiWan`（快玩）、`KuGou`（酷狗）、`leigod_person_7012`（雷神加速器）、`obs-studio` / `obs-studio-hook`（OBS 录屏）、`Oracle`（Java）、`Oray`/`OrayClient`（向日葵）、`Realtek`、`NVIDIA`/`NVIDIA Corporation`、`SogouInput`（搜狗输入法）、`Tencent`、`Thunder Network`（迅雷）、`VMware`、`Lenovo`、`iTop`、`IObit`、`AVS4YOU`、`Claude`（Claude 桌面数据）、`Package Cache`（VS/驱动安装缓存）、`Packages`、`SoftwareDistribution`（更新缓存）、`USOPrivate`/`USOShared`（更新会话）、`ssh`、`Nahimic`、`{GUID}.tmp` 若干（安装残留临时文件，可清）。

---

## 六、C:\Users\lenovo 一级（重点）

### 个人数据目录

| 目录 | 内容 |
|---|---|
| `Desktop` | 29 项：baokao、CC Switch、Charles、Deepseek-Harness-Desktop、Chrome、ida、jadx 等快捷方式与文件 |
| `Documents` | Codex、Deepseek-Harness-Desktop、leidian9/leidian14（雷电模拟器数据）、Navicat、Sunlogin Files（向日葵文件）、Tencent Files（微信/QQ 文件）、Visual Studio 2022/18、My Cheat Tables |
| `Downloads` | 基本为空 |
| `Pictures` | 截图、Camera Roll、联想安卓照片等 |
| `Music` / `Videos` / `Favorites` / `Contacts` / `OneDrive` | 标准用户目录 |
| `miniconda3` | Miniconda 基础环境 |
| `PycharmProjects` | PyCharm 项目目录 |
| `android` | Android 相关工程/数据 |
| `source` / `native` / `daemon` / `wrapper` / `caches` / `Doubao` | 来源不一的工作数据（部分为工具运行目录，`Doubao` 为豆包客户端数据） |
| `NTUSER.DAT*` | 用户注册表 hive（勿动） |

### 开发/工具配置（点目录）

| 目录 | 用途 |
|---|---|
| `.android` | Android SDK/AVD 配置与模拟器缓存 |
| `.gradle` | Gradle 构建缓存（含 jars-9 等依赖缓存，可清） |
| `.m2` | Maven 本地仓库 |
| `.nuget` / `.dotnet` | .NET/NuGet 包与 SDK 广告缓存 |
| `.conda` / `.anaconda` | conda 频道/包缓存 |
| `.EasyOCR` | EasyOCR 模型文件 |
| `.claude` / `.claude.json` / `.claude-code-gui` | Claude Code 配置、会话、插件、项目历史 |
| `.dsh` | DeepSeek Harness 配置：profiles（含 node_modules/web）、sessions、plugins、storages |
| `.cc-switch` | CC Switch（AI 服务切换器）配置 |
| `.copilot` | GitHub Copilot CLI/IDE 配置 |
| `.qoder` / `.roo-cline` / `.run-vs-agent` / `.th-client` / `.vscode` | AI 编程 IDE 与插件配置（Qoder/Roo Cline/VSCode 等） |
| `.vscode-shared` | VSCode 共享组件 |
| `.objection` | objection（移动安全工具）配置 |
| `.mitmproxy` | mitmproxy 抓包代理配置 |
| `.ssh` | SSH 密钥与配置 |
| `.gnupg` | GPG 密钥 |
| `.cache` | 工具缓存：codex-runtimes、huggingface（faster-whisper 模型）、douyin-link-video-distiller（浏览器 profile） |
| `.playwright-mcp` / `ms-playwright` | Playwright 浏览器缓存 |
| `.Ld9VirtualBox` | 雷电模拟器 9 的 VirtualBox 数据 |
| `.config` / `.gitconfig` / `.bash_history` 等 | git/终端配置 |
| `.idlerc` / `.matplotlib` / `.tmp` | Python 相关小配置与临时文件 |
| `.aigo123` | 爱购/aigo 安装器残留 |
| `「开始」菜单`、`Application Data`、`Cookies`、`Local Settings` 等 | 系统兼容链接（junction），勿手动清理 |

### AppData 软件清单（仅列名，均为该软件缓存/配置）

- `Local`（含）：Adobe、Google、Tencent、Bytedance、Doubao、Feishu/Lark、JianyingPro（剪映）、Quark/UC（夸克/UC）、Clash Plus、Claude/Claude-3p/Claude-Data、deepseek-harness-desktop-updater、dsh-desktop-updater、coze-updater、Everything、EVPlayer、fastpdf/lenovoPdf/sogoupdf、GitHubDesktop、JetBrains、mongodb、ms-playwright、node/npm-cache/pnpm/pnpm-cache、OpenAI、pip、qqkartliveupdate、RawEngine、skylot（jadx）、vmware、ghidra、frida、youdao/ynote-desktop-updater、Wooduan、z 等
- `Roaming`（含）：adspower_global（AdsPower）、Charles、Reqable、Claude、Code/Cursor（VSCode 系）、Coze、Deepseek-Harness-Desktop、dsh-desktop、Doubao、WXDrive、QQ、Quark、KuGou8、leidian9、LarkShell、360GameAssistant、Leigod 系、VMware、Hex-Rays（IDA 插件数据）、BinDiff、OBSRecorder、obs-studio、Python、微软系、baidu/baidunetdisk、ynote-desktop、Sogou 语音、NVIDIA、IObit、Lenovo 等大量软件
- `LocalLow`：Intel、IObit、Microsoft、NVIDIA、SogouPY（搜狗拼音）、iTop 等

---

## 七、可清理空间建议（仅提示，未代做）

| 项目 | 位置 | 预估 |
|---|---|---|
| 酷狗 P2P 缓存 | `C:\KuGou\Temp\tp2p` | 大（哈希文件数千） |
| Chrome 调试 profile | `C:\temp\chrome-debug-profile` | 数百 MB 级 |
| AdsPower 浏览器缓存 | `C:\.ADSPOWER_GLOBAL\cache` | 视使用量 |
| Gradle/NuGet/npm/pnpm/pip 缓存 | `C:\Users\lenovo\.gradle\caches`、`.nuget`、`AppData\Local\npm-cache`、`pnpm-cache`、`pip` | 数 GB 级 |
| Windows Update 缓存 | `C:\Windows\SoftwareDistribution` | 视更新量 |
| 系统休眠文件 | `C:\hiberfil.sys` | 9.5 GB（`powercfg /h off` 可关闭休眠释放） |
| 页面文件 | `C:\pagefile.sys` | 12.5 GB（建议保留，勿手动删） |
| 回收站 | `$Recycle.Bin` | 视内容 |
| 装机工具全家桶 | `Program Files (x86)` 下 Lds/Lhp/WinAuthority 等 | 软件体积+后台进程 |
| 雷电模拟器旧版本 | `Documents\leidian9` / `leidian14` | 视镜像大小，如不用可卸 |

> 删除任何系统目录前请以管理员身份操作并谨慎确认；`WinSxS`、`Installer`、`System Volume Information`、`NTUSER.DAT` 切勿手动删除。

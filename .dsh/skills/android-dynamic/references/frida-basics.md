# Frida 版本兼容与脚本基础（详细手册）

> 本文件由 `SKILL.md §1` 引用，属于**按需加载**层：对齐 frida-server 版本、处理 17.x API 差异、写 spawn/attach 命令与 Java/Native Hook 模板时读。写任何 Frida 脚本前先看这里。

---

# §1 Frida 版本兼容 + 真机基线（写脚本前必读）（待匹配路径）

🔴 **CHECKPOINT：写任何 Frida 脚本前确认 frida-server 版本与引擎。**

| server（真机） | 版本 | PC 客户端 | 适用 |
|---------------|------|-----------|------|
| `/data/local/tmp/florida-server` | 16.5.9（Florida 魔改免杀，自报 16.5.10-dev.0） | venv `.venv-frida-16.5.7`（**16.5.x↔16.5.x**） | **主力**，改名裸启动（§3.4） |
| `/data/local/tmp/f1657` | 16.5.7（官方） | venv `.venv-frida-16.5.7`（**16.5.x↔16.5.x**） | 官方回退 |
| `/data/local/tmp/frida-server` | 16.7.19（官方） | PC `frida` 16.7.19 | 普通目标 |

> 🔴 **17.x 在硬目标全挂**（XHS 所有模式秒退）；16.7.19 / 16.5.x 才是工作线。

| 触发条件 | 修复 |
|---------|------|
| `Module.findExportByName is not a function`（17.9.1+ 移除） | 改 `Process.findModuleByName('libc.so').findExportByName('fopen')` |
| undetected-frida-server | 只有 `Module.getGlobalExportByName(name, module)`，**参数顺序相反**：`getGlobalExportByName('strstr','libc.so')` |
| 17.x Duktape 语法报错 | **禁用** `===`/`let`/`const`/箭头函数/`String.includes()`/`for...of`；改 `var`/`==`/`indexOf`/普通 `for` |
| `send()` 大数据被截断 | 单条约 16KB 上限 → 分块发送或落盘再 pull（大二进制 dump 见 §5 send-dump） |

```powershell
.\.venv-frida-16.5.7\Scripts\frida.exe -U -f <包名> -l hook.js --no-pause   # spawn（推荐，bypass 在初始化前生效）
.\.venv-frida-16.5.7\Scripts\frida.exe -U <包名> -l hook.js                  # attach 运行中（硬壳禁用，见 §3.4）
```

```javascript
// Java（Duktape 兼容）
Java.perform(function() {
    var T = Java.use("com.example.TargetClass");
    T.targetMethod.implementation = function(a, b) {
        var r = this.targetMethod(a, b);
        console.log("[+] args:", a, b, "ret:", r);
        return r;
    };
});
// Native
var fopen = Process.findModuleByName("libc.so").findExportByName("fopen");
Interceptor.attach(fopen, { onEnter: function(args){ console.log("[+] fopen:", args[0].readUtf8String()); }});
```

# hooker/

通用可复用 Frida 库（非项目专属）。

- `js/`：通用 hook 脚本（SSL、脱壳、内存扫描等）
- `hooker.py`：Frida 通用加载器（spawn/attach、批量注入）

项目专属 hook 放 `projects/<target>/hooks/`，不落这里。

#!/usr/bin/env python3
"""hooker.py - 通用 Frida 加载器骨架。

项目专属逻辑放 projects/<target>/scripts/，这里只保留可复用的 spawn/attach 通用入口。
"""


def main() -> None:
    raise NotImplementedError("通用加载器骨架，待按目标填充")


if __name__ == "__main__":
    main()

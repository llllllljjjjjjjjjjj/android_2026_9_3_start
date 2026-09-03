# -*- coding: utf-8 -*-
"""unidbg-mcp — unidbg 离线 SO 参数生成 MCP（JPype 进程内调 jar）。

前置：unidbg 补环境 Java 工程已字节级验证 → shade 打 fat jar。
工具：generate —— 进程内直调 Java 补环境类生成 SO 参数。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from android_mcp.common.mcp_stdio import StdioMcpServer, object_schema, string_prop
from android_mcp.servers.unidbg_mcp import unidbg_ops

server = StdioMcpServer("unidbg-mcp", "0.1.0")


@server.tool(
    "generate",
    "调用 unidbg 补环境后的 SO 参数生成器（离线，JPype 进程内直调 jar）。"
    "前置：Java 层已字节级验证并 shade 打 jar（见 protocol-signature-reverser SKILL Phase 6.1）。",
    object_schema(
        {"input": string_prop("传给生成器的输入（语义由 Java 侧补环境类决定）。")},
        required=["input"],
    ),
)
def generate(input: str):
    return unidbg_ops.generate(input)


if __name__ == "__main__":
    server.run()

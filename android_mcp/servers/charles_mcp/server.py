# -*- coding: utf-8 -*-
"""charles-mcp — Charles Proxy 抓包会话读取 MCP

前置：Charles GUI 开启 Web Interface（Proxy → Web Interface Settings → Enable，默认 8888）。
提供：会话导出 / 按 URL 正则查找请求 / 录制开关 / 会话落盘。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from android_mcp.common.mcp_stdio import StdioMcpServer, bool_prop, int_prop, object_schema, string_prop
from android_mcp.servers.charles_mcp import charles_api

server = StdioMcpServer("charles-mcp", "0.1.0")


@server.tool(
    "charles_find",
    "从 Charles 当前录制会话中按 URL 正则/子串查找请求，返回 url/method/status/headers/body 摘要。"
    "（需要 Charles 已开启 Web Interface：Proxy → Web Interface Settings → Enable）",
    object_schema(
        {
            "pattern": string_prop("URL 正则或子串；空 = 全部。"),
            "method": string_prop("HTTP 方法过滤（如 GET/POST）。"),
            "port": int_prop("Charles Web Interface 端口。", 8888, 1, 65535),
            "limit": int_prop("最多返回条数。", 20, 1, 200),
        },
        required=[],
    ),
)
def charles_find(pattern: str = "", method: str = "", port: int = 8888, limit: int = 20):
    try:
        return {"entries": charles_api.find_entries(port, pattern, method, limit)}
    except charles_api.CharlesApiError as e:
        return {"error": str(e)}


@server.tool(
    "charles_export",
    "导出 Charles 当前会话并保存到文件（默认 projects/dy/capture/charles_session.json）。",
    object_schema(
        {
            "port": int_prop("Charles Web Interface 端口。", 8888, 1, 65535),
            "dest": string_prop("保存路径；空 = 默认 capture/charles_session.json。"),
        },
        required=[],
    ),
)
def charles_export(port: int = 8888, dest: str = ""):
    try:
        return charles_api.save_session(port, dest)
    except charles_api.CharlesApiError as e:
        return {"error": str(e)}


@server.tool(
    "charles_recording",
    "控制 Charles 录制开关：start / stop / status。",
    object_schema(
        {
            "action": string_prop("start / stop / status"),
            "port": int_prop("Charles Web Interface 端口。", 8888, 1, 65535),
        },
        required=["action"],
    ),
)
def charles_recording(action: str = "status", port: int = 8888):
    try:
        return charles_api.recording(port, action)
    except charles_api.CharlesApiError as e:
        return {"error": str(e)}


if __name__ == "__main__":
    server.run()

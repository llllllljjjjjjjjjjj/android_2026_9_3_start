from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from android_mcp.common.mcp_stdio import StdioMcpServer, bool_prop, int_prop, object_schema, string_prop
from android_mcp.servers.reverse_index_mcp import reverse_index


server = StdioMcpServer("reverse-index-mcp", "0.1.0")


@server.tool(
    "index_project",
    "Index jadx/apktool decompiled sources for a target under projects/<target>.",
    object_schema(
        {
            "target": string_prop("Target directory name under projects/."),
            "decompiled_path": string_prop("Optional absolute or relative decompiled source path."),
            "force": bool_prop("Rebuild the whole index.", False),
            "max_file_mb": int_prop("Skip files larger than this many MB.", 5, 1, 200),
        },
        required=["target"],
    ),
)
def index_project(target: str, decompiled_path: str | None = None, force: bool = False, max_file_mb: int = 5):
    return reverse_index.index_project(target, decompiled_path or None, force, max_file_mb)


@server.tool(
    "search_code",
    "Search indexed source lines.",
    object_schema(
        {
            "target": string_prop("Target directory name under projects/."),
            "query": string_prop("Keyword or regex."),
            "regex": bool_prop("Treat query as Python regex.", False),
            "limit": int_prop("Max results.", 50, 1, 500),
        },
        required=["target", "query"],
    ),
)
def search_code(target: str, query: str, regex: bool = False, limit: int = 50):
    return reverse_index.search_code(target, query, regex, limit)


@server.tool(
    "search_strings",
    "Search indexed string literals.",
    object_schema({"target": string_prop("Target."), "query": string_prop("String keyword."), "limit": int_prop("Max results.", 50, 1, 500)}, required=["target", "query"]),
)
def search_strings(target: str, query: str, limit: int = 50):
    return reverse_index.search_table(target, "strings", "value", query, limit)


@server.tool(
    "find_endpoint",
    "Find URL/Retrofit/OkHttp endpoint anchors.",
    object_schema({"target": string_prop("Target."), "query": string_prop("Host/path/keyword."), "limit": int_prop("Max results.", 50, 1, 500)}, required=["target", "query"]),
)
def find_endpoint(target: str, query: str, limit: int = 50):
    return reverse_index.search_table(target, "endpoints", "value", query, limit)


@server.tool(
    "find_symbol",
    "Find indexed class/method symbols by name.",
    object_schema({"target": string_prop("Target."), "name": string_prop("Symbol name keyword."), "limit": int_prop("Max results.", 50, 1, 500)}, required=["target", "name"]),
)
def find_symbol(target: str, name: str, limit: int = 50):
    return reverse_index.find_symbol(target, name, limit)


@server.tool(
    "find_references",
    "Find textual references to a symbol or method name.",
    object_schema({"target": string_prop("Target."), "symbol": string_prop("Symbol text to search."), "limit": int_prop("Max results.", 50, 1, 500)}, required=["target", "symbol"]),
)
def find_references(target: str, symbol: str, limit: int = 50):
    return reverse_index.search_code(target, symbol, False, limit)


@server.tool(
    "list_suspicious_sign_methods",
    "List methods/classes whose names or declarations look related to signatures, tokens or crypto.",
    object_schema({"target": string_prop("Target."), "limit": int_prop("Max results.", 80, 1, 500)}, required=["target"]),
)
def list_suspicious_sign_methods(target: str, limit: int = 80):
    return reverse_index.list_suspicious_sign_methods(target, limit)


@server.tool(
    "open_source",
    "Return source lines around a file and line number from the index.",
    object_schema(
        {
            "target": string_prop("Target."),
            "file": string_prop("Indexed relative path or suffix."),
            "line": int_prop("Line number.", 1, 1, None),
            "context": int_prop("Context lines before and after.", 8, 0, 80),
        },
        required=["target", "file"],
    ),
)
def open_source(target: str, file: str, line: int = 1, context: int = 8):
    return reverse_index.open_source(target, file, line, context)


if __name__ == "__main__":
    server.run()


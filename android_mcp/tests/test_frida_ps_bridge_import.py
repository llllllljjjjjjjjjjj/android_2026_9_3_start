"""Regression: frida_ps spawned bridge must import os before os.environ.

2026-08-18 Maoyan session: MCP frida_ps crashed with NameError because the
generated bridge used os.environ but only imported json/frida.
"""
from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from android_mcp.servers.frida_orchestrator_mcp import frida_ops  # noqa: E402


def _embedded_bridge_source() -> str:
    src = inspect.getsource(frida_ops.frida_ps)
    start = src.find('bridge.write_text(')
    if start < 0:
        raise AssertionError("frida_ps no longer writes a bridge script")
    chunk = src[start:]
    # First triple-quoted string after write_text is the spawned script.
    q = chunk.find('"""')
    if q < 0:
        q = chunk.find("'''")
        end = chunk.find("'''", q + 3)
        return chunk[q + 3 : end]
    end = chunk.find('"""', q + 3)
    return chunk[q + 3 : end]


def main() -> int:
    bridge = _embedded_bridge_source()
    tree = ast.parse(bridge)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    uses_os = "os.environ" in bridge or "os.getenv" in bridge
    ok = (not uses_os) or ("os" in imported)
    print("uses_os_environ=", uses_os)
    print("imports_os=", "os" in imported)
    print("PASS" if ok else "FAIL: frida_ps bridge uses os but does not import it")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

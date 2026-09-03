from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable
SERVERS = [
    ROOT / "android_mcp" / "servers" / "reverse_index_mcp" / "server.py",
    ROOT / "android_mcp" / "servers" / "frida_orchestrator_mcp" / "server.py",
    ROOT / "android_mcp" / "servers" / "algo_lab_mcp" / "server.py",
]


def call_server(server_path: Path, method: str, params: dict | None = None) -> dict:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    proc = subprocess.run(
        [PY, str(server_path)],
        input=json.dumps(payload, ensure_ascii=False) + "\n",
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(ROOT),
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{server_path} exited {proc.returncode}: {proc.stderr}")
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f"{server_path} produced no response; stderr={proc.stderr}")
    return json.loads(lines[-1])


def main() -> None:
    for server in SERVERS:
        init_resp = call_server(server, "initialize", {"protocolVersion": "2025-06-18"})
        assert "result" in init_resp, init_resp
        tools_resp = call_server(server, "tools/list")
        tools = tools_resp["result"]["tools"]
        assert tools, f"no tools listed for {server}"
        print(f"OK {server.name}: {len(tools)} tools")


if __name__ == "__main__":
    main()

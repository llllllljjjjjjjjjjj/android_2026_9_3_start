#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""smoke-mcp.py — 模拟 DSH mcp-client 对 mcp-bridge.py 启动的 server 做 MCP 握手冒烟测试。

用法: python android_mcp\\scripts\\smoke-mcp.py [reverse_index|frida_orchestrator|algo_lab|charles]
验证: initialize -> notifications/initialized -> tools/list 全链路。
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SERVER_TYPE = sys.argv[1] if len(sys.argv) > 1 else "reverse_index"
PYTHON = os.environ.get("ANDROID_MCP_PYTHON", sys.executable)
BRIDGE = ROOT / "android_mcp" / "mcp-bridge.py"
if not BRIDGE.exists():
    sys.exit(f"missing {BRIDGE}")

env = os.environ.copy()
env["ANDROID_MCP_PROJECT_ROOT"] = str(ROOT)
extra = [str(ROOT / "android_mcp" / "common"), str(ROOT / "android_mcp" / "toolchain" / "python" / "vendor")]
env["PYTHONPATH"] = os.pathsep.join(extra + ([env.get("PYTHONPATH", "")] if env.get("PYTHONPATH") else []))
env["PATH"] = str(ROOT / "android_mcp" / "toolchain" / "bin" / "windows" / "platform-tools") + os.pathsep + env.get("PATH", "")

stdout_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".out", mode="w+b")
stderr_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".err", mode="w+b")
stdout_tmp.close()
stderr_tmp.close()

proc = subprocess.Popen(
    [PYTHON, str(BRIDGE), SERVER_TYPE],
    stdin=subprocess.PIPE,
    stdout=open(stdout_tmp.name, "wb"),
    stderr=open(stderr_tmp.name, "wb"),
    cwd=str(ROOT),
    env=env,
)

def send(obj):
    proc.stdin.write((json.dumps(obj) + "\n").encode("utf-8"))
    proc.stdin.flush()

_read_pos = [0]

def read_response(timeout=15):
    """MCP 响应是单行 JSON；跨调用保留已读位置，轮询读文件尾部直到拿到新行或超时。"""
    import time
    deadline = time.time() + timeout
    buf = b""
    while time.time() < deadline:
        if proc.poll() is not None and os.path.getsize(stdout_tmp.name) == _read_pos[0]:
            time.sleep(0.1)
            continue
        with open(stdout_tmp.name, "rb") as f:
            f.seek(_read_pos[0])
            chunk = f.read()
        _read_pos[0] += len(chunk)
        buf += chunk
        text = buf.decode("utf-8", "replace")
        lines = [l for l in text.splitlines() if l.strip()]
        if lines:
            try:
                return json.loads(lines[0])
            except json.JSONDecodeError:
                time.sleep(0.2)
        time.sleep(0.2)
    return None

ok = True
try:
    send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
          "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                     "clientInfo": {"name": "smoke", "version": "0.0.1"}}})
    r = read_response()
    if r is None or "error" in (r or {}):
        ok = False
        print(f"FAIL initialize: {r}")
    else:
        print(f"OK  initialize  serverInfo={r['result']['serverInfo']}")

    send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    r = read_response()
    if r is None or "error" in (r or {}):
        ok = False
        print(f"FAIL tools/list: {r}")
    else:
        tools = r["result"]["tools"]
        print(f"OK  tools/list  {len(tools)} tools: {', '.join(t['name'] for t in tools[:8])}{' ...' if len(tools) > 8 else ''}")

    if ok:
        send({"jsonrpc": "2.0", "id": 3, "method": "ping", "params": {}})
        r = read_response()
        print(("OK  ping" if r and "result" in r else f"FAIL ping: {r}"))
        ok = ok and r and "result" in r
finally:
    proc.kill()
    proc.wait()
    err = open(stderr_tmp.name, "rb").read().decode("utf-8", "replace")
    if err.strip():
        print("--- server stderr (tail) ---")
        print("\n".join(err.strip().splitlines()[-5:]))
    for p in (stdout_tmp.name, stderr_tmp.name):
        try:
            os.unlink(p)
        except OSError:
            pass

sys.exit(0 if ok else 1)

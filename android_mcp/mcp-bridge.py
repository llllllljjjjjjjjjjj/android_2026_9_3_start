#!/usr/bin/env python3
"""
MCP Server Bridge — 可移植入口
================================
自动发现 android_mcp 目录，消除硬编码绝对路径。

用法：
    python android_mcp/mcp-bridge.py <server_type>

<server_type> 映射到 android_mcp/servers/<name>_mcp/server.py
    frida_orchestrator  →  frida_orchestrator_mcp/server.py
    reverse_index       →  reverse_index_mcp/server.py
    algo_lab            →  algo_lab_mcp/server.py

环境变量：
    ANDROID_MCP_PYTHON       → 指定 Python 解释器（默认：sys.executable）
    ANDROID_MCP_PROJECT_ROOT → 强制项目根目录（默认：自动发现）
"""

import os
import sys
import subprocess
from pathlib import Path


def find_project_root() -> Path:
    """根据本脚本位置自动发现项目根目录。"""
    env_root = os.environ.get("ANDROID_MCP_PROJECT_ROOT")
    if env_root:
        return Path(env_root).resolve()
    # 本脚本位于 android_mcp/mcp-bridge.py → 上级即项目根
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent


def resolve_server_script(project_root: Path, server_type: str) -> Path:
    """拼接 android_mcp/servers/<name>_mcp/server.py"""
    mapping = {
        "frida_orchestrator": "frida_orchestrator_mcp",
        "reverse_index": "reverse_index_mcp",
        "algo_lab": "algo_lab_mcp",
        "charles": "charles_mcp",
        "unidbg": "unidbg_mcp",
    }
    if server_type not in mapping:
        raise SystemExit(f"[mcp-bridge] 未知 server_type: {server_type}. 可用: {list(mapping.keys())}")
    server_dir = mapping[server_type]
    script = project_root / "android_mcp" / "servers" / server_dir / "server.py"
    if not script.exists():
        raise SystemExit(
            f"[mcp-bridge] 找不到 server 脚本: {script}\n"
            f"  请确认 android_mcp/ 位于项目根下，或设置 ANDROID_MCP_PROJECT_ROOT"
        )
    return script


def find_python() -> str:
    """按优先级寻找合适的 Python 解释器。"""
    env_python = os.environ.get("ANDROID_MCP_PYTHON")
    if env_python:
        return env_python
    # 优先用当前解释器（确保能 import 已装包）
    return sys.executable


def main():
    if len(sys.argv) < 2:
        raise SystemExit("用法: python mcp-bridge.py <server_type>")

    server_type = sys.argv[1]
    project_root = find_project_root()
    server_script = resolve_server_script(project_root, server_type)
    python = find_python()

    # 可选：把 android_mcp/common 和 toolchain/python/vendor 加入 PYTHONPATH
    env = os.environ.copy()
    extra_paths = []

    # 项目根入 PYTHONPATH，使 server 能 `import android_mcp.common`（22222 server 风格）
    extra_paths.append(str(project_root))

    common_dir = project_root / "android_mcp" / "common"
    if common_dir.exists():
        extra_paths.append(str(common_dir))

    vendor_dir = project_root / "android_mcp" / "toolchain" / "python" / "vendor"
    if vendor_dir.exists():
        extra_paths.append(str(vendor_dir))

    if extra_paths:
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = os.pathsep.join(extra_paths + ([existing] if existing else []))

    # 把 bundled platform-tools 加入 PATH，确保 adb 可被找到
    platform_tools = project_root / "android_mcp" / "toolchain" / "bin" / "windows" / "platform-tools"
    if platform_tools.exists():
        existing_path = env.get("PATH", "")
        env["PATH"] = str(platform_tools) + os.pathsep + existing_path

    # 传递项目根给 MCP server（部分 server 的 paths.py 会读取）
    env["ANDROID_MCP_PROJECT_ROOT"] = str(project_root)

    # 启动 MCP server
    cmd = [python, str(server_script)]
    # 透传剩余参数（如有）
    cmd.extend(sys.argv[2:])

    # stderr 打印诊断信息（stdout/stderr 交给 MCP 协议）
    print(f"[mcp-bridge] project_root={project_root}", file=sys.stderr)
    print(f"[mcp-bridge] launching {server_script} with {python}", file=sys.stderr)

    try:
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

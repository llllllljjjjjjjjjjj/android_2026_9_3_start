from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional


def project_root() -> Path:
    env_root = os.environ.get("ANDROID_MCP_PROJECT_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return Path(__file__).resolve().parents[2]


def android_mcp_root() -> Path:
    return project_root() / "android_mcp"


def toolchain_root() -> Path:
    return android_mcp_root() / "toolchain"


def bundled_platform_tools_dir() -> Path:
    return toolchain_root() / "bin" / "windows" / "platform-tools"


def bundled_adb_path() -> Path:
    exe = "adb.exe" if os.name == "nt" else "adb"
    return bundled_platform_tools_dir() / exe


def bundled_frida_server_path(abi: str = "arm64-v8a") -> Path:
    # Only an arm64-v8a patched server is bundled today. abi stays in the signature
    # so callers keep working once more ABIs land under toolchain/device/frida.
    server_name = "new-server-arm64-16.5.8-dev.11"
    return toolchain_root() / "device" / "frida" / server_name


def bundled_algorithm_aide_apk() -> Path:
    primary = toolchain_root() / "apks" / "algorithm-aide-pro-1.0.9-109.apk"
    if primary.exists():
        return primary
    return toolchain_root() / "apks" / "device-tools" / "com.junge.algorithmAidePro.apk"


def bundled_device_tool_apk(package: str) -> Path:
    return toolchain_root() / "apks" / "device-tools" / f"{package}.apk"


def bundled_python_vendor_dir() -> Path:
    return toolchain_root() / "python" / "vendor"


def bundled_env(extra: Optional[dict[str, str]] = None) -> dict[str, str]:
    env = os.environ.copy()
    vendor = bundled_python_vendor_dir()
    if vendor.exists():
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(vendor) if not existing else str(vendor) + os.pathsep + existing
        if str(vendor) not in sys.path:
            sys.path.insert(0, str(vendor))
    platform_tools = bundled_platform_tools_dir()
    if platform_tools.exists():
        existing_path = env.get("PATH", "")
        env["PATH"] = str(platform_tools) if not existing_path else str(platform_tools) + os.pathsep + existing_path
    if extra:
        env.update(extra)
    return env


def resolve_under_root(path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = project_root() / candidate
    return candidate.resolve()


def target_root(target: str) -> Path:
    if not target or ".." in target or any(ch in target for ch in "\\/:*?\"<>|"):
        raise ValueError("target must be a non-empty ASCII-safe project directory name")
    projects = (project_root() / "projects").resolve()
    root = (projects / target).resolve()
    if projects not in root.parents:
        raise ValueError("target must resolve to a direct child of projects/")
    if not root.exists():
        raise ValueError(f"target project not found: {root}")
    return root


def target_artifacts(target: str) -> Path:
    path = target_root(target) / "artifacts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def target_hooks(target: str) -> Path:
    path = target_root(target) / "hooks"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_decompiled_path(target: str) -> Path:
    return target_root(target) / "decompiled"


def safe_output_path(base: Path, requested: Optional[str], default_name: str) -> Path:
    if requested:
        out = Path(requested)
        if not out.is_absolute():
            out = base / out
    else:
        out = base / default_name
    out = out.resolve()
    base_resolved = base.resolve()
    if base_resolved not in out.parents and out != base_resolved:
        raise ValueError(f"output path must stay under {base_resolved}")
    out.parent.mkdir(parents=True, exist_ok=True)
    return out

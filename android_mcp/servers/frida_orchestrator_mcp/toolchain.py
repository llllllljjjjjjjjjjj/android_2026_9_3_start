from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from android_mcp.common.paths import bundled_algorithm_aide_apk, bundled_env, bundled_frida_server_path, bundled_platform_tools_dir, project_root, toolchain_root
from android_mcp.common.process import run_command
from android_mcp.common.adb import adb_path, choose_real_serial, list_devices

ALGORITHM_AIDE_PACKAGE = "com.junge.algorithmAidePro"
HIDE_MY_APPLIST_PACKAGE = "com.tsng.hidemyapplist"
REQABLE_PACKAGE = "com.reqable.android"
ALGORITHM_AIDE_APK = Path(os.environ.get("ANDROID_MCP_ALGO_AIDE_APK", str(bundled_algorithm_aide_apk())))
PATCHED_FRIDA_SERVER = Path(os.environ.get("ANDROID_MCP_PATCHED_FRIDA_SERVER", str(bundled_frida_server_path())))
REMOTE_PATCHED_FRIDA = os.environ.get("ANDROID_MCP_REMOTE_PATCHED_FRIDA", "/data/local/tmp/new-server")


"""Portable toolchain and first-run bootstrap helpers."""

def frida_path() -> str:
    return sys.executable


def frida_ps_path() -> str:
    return sys.executable


def frida_ls_devices_path() -> str:
    return sys.executable


def frida_device_selector() -> list[str]:
    explicit = os.environ.get("ANDROID_MCP_FRIDA_DEVICE", "").strip()
    if explicit:
        return ["-D", explicit]
    return ["-U"]


def _mcp_env(extra: Optional[dict[str, str]] = None) -> dict[str, str]:
    return bundled_env(extra)


def _frida_module_args(tool_name: str) -> list[str]:
    module = {
        "frida": "frida_tools.repl",
        "frida-ps": "frida_tools.ps",
        "frida-ls-devices": "frida_tools.lsd",
    }[tool_name]
    return [sys.executable, "-m", module]


def _tool_exists(path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "size": path.stat().st_size if path.exists() and path.is_file() else None,
    }


def toolchain_status(serial: Optional[str] = None) -> Dict[str, object]:
    """Report the portable android_mcp toolchain that this server will use."""
    vendor = toolchain_root() / "python" / "vendor"
    device_tools = toolchain_root() / "apks" / "device-tools"
    apks = []
    if device_tools.exists():
        apks = [
            {"package": apk.stem, "path": str(apk), "size": apk.stat().st_size}
            for apk in sorted(device_tools.glob("*.apk"))
        ]
    device_summary: Dict[str, object] | None = None
    try:
        devices = list_devices(real_only=False)
        selected = choose_real_serial(serial) if devices else None
        device_summary = {"devices": devices, "selected": selected}
    except Exception as exc:  # noqa: BLE001 - status surface should not fail hard
        device_summary = {"error": str(exc)}
    return {
        "project_root": str(project_root()),
        "toolchain_root": str(toolchain_root()),
        "platform_tools": str(bundled_platform_tools_dir()),
        "adb": _tool_exists(Path(adb_path())),
        "algorithm_aide_apk": _tool_exists(Path(ALGORITHM_AIDE_APK)),
        "patched_frida_server": _tool_exists(Path(PATCHED_FRIDA_SERVER)),
        "remote_patched_frida": REMOTE_PATCHED_FRIDA,
        "python": sys.executable,
        "python_vendor": {"path": str(vendor), "exists": vendor.exists()},
        "bundled_reverse_apks": apks,
        "device": device_summary,
    }


def adb_connect(endpoint: str, timeout: int = 30) -> Dict[str, object]:
    start = run_command([adb_path(), "start-server"], timeout=timeout)
    connect = run_command([adb_path(), "connect", endpoint], timeout=timeout)
    devices = {"devices": list_devices(real_only=False)}
    return {"endpoint": endpoint, "start_server": start, "connect": connect, "devices": devices}


def install_bundled_reverse_apks(
    serial: Optional[str] = None,
    packages: Optional[List[str]] = None,
    reinstall: bool = True,
    grant: bool = True,
    timeout: int = 300,
) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    device_tools = toolchain_root() / "apks" / "device-tools"
    if not device_tools.exists():
        raise ValueError(f"bundled APK directory not found: {device_tools}")
    requested = set(packages or [])
    candidates = sorted(device_tools.glob("*.apk"))
    if requested:
        candidates = [apk for apk in candidates if apk.stem in requested]
    from .package_ops import install_apk

    installs = []
    for apk in candidates:
        try:
            installs.append({"package": apk.stem, "apk": str(apk), "result": install_apk(serial_chosen, str(apk), reinstall=reinstall, grant=grant)})
        except Exception as exc:  # noqa: BLE001 - continue installing remaining tool APKs
            installs.append({"package": apk.stem, "apk": str(apk), "error": str(exc)})
    missing = sorted(requested - {apk.stem for apk in candidates})
    return {"serial": serial_chosen, "installed": installs, "missing": missing, "timeout": timeout}


def bootstrap_device_toolchain(
    serial: Optional[str] = None,
    tcp_endpoint: Optional[str] = None,
    install_algorithm_aide_apk: bool = True,
    install_cached_tool_apks: bool = False,
    start_frida_server: bool = True,
) -> Dict[str, object]:
    from .adb_ops import adb_root_shell, device_health
    from .algorithm_aide_ops import setup_algorithm_aide
    from .frida_ops import push_patched_frida_server, start_patched_frida_server

    steps: Dict[str, object] = {"toolchain": toolchain_status(serial)}
    if tcp_endpoint:
        steps["adb_connect"] = adb_connect(tcp_endpoint)
    serial_chosen = choose_real_serial(serial)
    steps["serial"] = serial_chosen
    steps["root"] = adb_root_shell(serial_chosen, "id", timeout=15)
    if install_algorithm_aide_apk:
        steps["algorithm_aide"] = setup_algorithm_aide(serial_chosen, str(ALGORITHM_AIDE_APK), launch=False)
    if install_cached_tool_apks:
        steps["cached_tool_apks"] = install_bundled_reverse_apks(serial_chosen)
    steps["push_frida_server"] = push_patched_frida_server(serial_chosen, str(PATCHED_FRIDA_SERVER), REMOTE_PATCHED_FRIDA)
    if start_frida_server:
        steps["start_frida_server"] = start_patched_frida_server(serial_chosen, REMOTE_PATCHED_FRIDA)
    steps["final_health"] = device_health(serial_chosen)
    return steps

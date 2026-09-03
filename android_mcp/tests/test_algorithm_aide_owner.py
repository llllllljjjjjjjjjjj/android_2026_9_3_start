"""Regression: AlgorithmAide config must be written as system:system.

2026-08-18: MCP-written junge config landed root:root because the
algorithm_aide_* writers called root_push_file without owner and mkdir -p ran
as root. On device this produced e.g.
    /data/system/junge/com.android.vending/config.json  root root 0600
while the app itself (system uid) writes
    /data/system/junge/com.xingin.xhs/config.json       system system 0600
so the system-uid app could not read/manage MCP-written config.

This test is offline: it monkeypatches adb_root_shell to capture the emitted
shell, and checks the source of the three writers passes owner=system:system.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from android_mcp.servers.frida_orchestrator_mcp import algorithm_aide_ops as A  # noqa: E402


def _check_dir_fixer() -> list[str]:
    """Drive _fix_junge_dir_owner with a fake root shell and return failures."""
    failures: list[str] = []
    captured: list[str] = []
    original = A.adb_root_shell
    A.adb_root_shell = lambda serial, command, timeout=30: (captured.append(command) or {"returncode": 0})
    try:
        # config.json: fix the <pkg> dir, never the junge root.
        captured.clear()
        A._fix_junge_dir_owner("X", "/data/system/junge/com.foo.bar/config.json")
        cmd = captured[-1] if captured else ""
        if "chown system:system" not in cmd:
            failures.append(f"config: missing chown system:system -> {cmd!r}")
        if "/data/system/junge/com.foo.bar" not in cmd:
            failures.append(f"config: did not target <pkg> dir -> {cmd!r}")
        if "'/data/system/junge'" in cmd or "chown system:system /data/system/junge " in cmd:
            failures.append(f"config: must not chown junge root -> {cmd!r}")

        # frida script: fix both <pkg> and <pkg>/frida.
        captured.clear()
        A._fix_junge_dir_owner("X", "/data/system/junge/com.foo.bar/frida/h.js")
        cmd = captured[-1] if captured else ""
        if "/data/system/junge/com.foo.bar/frida" not in cmd:
            failures.append(f"frida: did not target frida dir -> {cmd!r}")
        if "/data/system/junge/com.foo.bar'" not in cmd and "/data/system/junge/com.foo.bar " not in cmd:
            failures.append(f"frida: did not also target <pkg> dir -> {cmd!r}")

        # AppSwitch.json sits directly under junge -> nothing to re-own.
        captured.clear()
        res = A._fix_junge_dir_owner("X", "/data/system/junge/AppSwitch.json")
        if res is not None or captured:
            failures.append("appswitch: should be a no-op (no dir under junge root)")

        # Paths outside junge must be ignored entirely.
        captured.clear()
        res = A._fix_junge_dir_owner("X", "/sdcard/Android/data/x/files/config/y.json")
        if res is not None or captured:
            failures.append("sdcard: must not chown anything outside junge")
    finally:
        A.adb_root_shell = original
    return failures


def _check_package_sanitizer() -> list[str]:
    failures: list[str] = []
    try:
        A._junge_package("../etc")
        failures.append("traversal package must raise")
    except ValueError:
        pass
    try:
        A._junge_package("com/foo")
        failures.append("slash package must raise")
    except ValueError:
        pass
    if A._junge_package("com.foo.bar") != "com.foo.bar":
        failures.append("normal package name should pass through")
    return failures


def _check_writer_source() -> list[str]:
    failures: list[str] = []
    checks = {
        "algorithm_aide_write_json": {"owner": True, "dir_fix": True},
        "algorithm_aide_set_appswitch": {"owner": True, "dir_fix": False},
        "algorithm_aide_write_frida_script": {"owner": True, "dir_fix": True},
    }
    for name, want in checks.items():
        src = inspect.getsource(getattr(A, name))
        # Only inspect root_push_file calls that target the junge system path,
        # not the sdcard mirror.
        junge_pushes = [
            ln for ln in src.splitlines()
            if "root_push_file" in ln and "sdcard" not in ln.lower()
        ]
        if want["owner"] and not any("owner=_JUNGE_OWNER" in ln or 'owner="system:system"' in ln for ln in junge_pushes):
            failures.append(f"{name}: junge root_push_file call must pass owner=system:system")
        if want["dir_fix"] and "_fix_junge_dir_owner" not in src:
            failures.append(f"{name}: must call _fix_junge_dir_owner")
    return failures


def main() -> int:
    failures = _check_dir_fixer() + _check_writer_source() + _check_package_sanitizer()
    if failures:
        print("FAIL")
        for f in failures:
            print(" -", f)
        return 1
    print("PASS: junge config writers stamp system:system and re-own dir chain")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

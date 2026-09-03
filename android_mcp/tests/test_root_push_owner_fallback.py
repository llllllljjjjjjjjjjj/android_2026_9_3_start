"""Regression: root_push_file must not leave new files as root:root.

2026-08-18: files written into an app-private dir (/data/user/0/<pkg>) or a
system dir inherit root:root on FIRST write, because the owner-preservation only
stat-ed the (absent) target file. On device, HMA's config lives at
    /data/user/0/com.tsng.hidemyapplist/files/config.json  owner 10270:10270
so a root:root config is unreadable by the app. The fix falls back to the parent
dir's owner when the file does not yet exist.

Offline: monkeypatch the adb layer and assert the emitted install shell.
"""
from __future__ import annotations

import posixpath
import shlex
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from android_mcp.servers.frida_orchestrator_mcp import root_ops as R  # noqa: E402


def _capture_install_cmd(remote: str, owner=None) -> str:
    captured: list[str] = []
    saved = {
        "choose_real_serial": R.choose_real_serial,
        "adb_args": R.adb_args,
        "run_command": R.run_command,
        "adb_root_shell": R.adb_root_shell,
    }
    R.choose_real_serial = lambda serial=None: "TESTSER"
    R.adb_args = lambda serial=None: ["adb"]
    R.run_command = lambda *a, **k: {"returncode": 0}
    R.adb_root_shell = lambda serial, command, timeout=120: (captured.append(command) or {"returncode": 0})
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            fh.write("{}")
            local = fh.name
        R.root_push_file(None, local, remote, mode="600", owner=owner)
    finally:
        for k, v in saved.items():
            setattr(R, k, v)
        try:
            Path(local).unlink()
        except OSError:
            pass
    # First adb_root_shell call is the install; second is the tmp cleanup.
    return captured[0] if captured else ""


def main() -> int:
    failures: list[str] = []

    # --- owner=None into an app-private dir: walk missing parents, inherit ancestor --- #
    remote = "/data/user/0/com.tsng.hidemyapplist/files/config.json"
    parent = posixpath.dirname(remote)
    cmd = _capture_install_cmd(remote, owner=None)
    if "need_dirs=" not in cmd or "dirname" not in cmd:
        failures.append(f"missing missing-dir walk (need_dirs/dirname): {cmd!r}")
    if cmd.count("stat -c") < 4:
        failures.append(f"expected >=4 stat probes (file %U/%u + ancestor %U/%u), got {cmd.count('stat -c')}: {cmd!r}")
    if f"{remote} 2>/dev/null" not in cmd:
        failures.append("missing stat of the target file itself")
    if "chown \"$owner\" $need_dirs" not in cmd:
        failures.append("must chown newly created intermediate dirs, not only the file")
    if "mkdir -p" not in cmd or "cp -f" not in cmd:
        failures.append("install shell malformed")
    if parent not in cmd:
        failures.append("parent path missing from walk/mkdir")

    # --- explicit owner: literal stamp, still walks missing dirs so new parents get owned --- #
    cmd2 = _capture_install_cmd("/data/system/junge/com.foo/config.json", owner="system:system")
    if f"owner={shlex.quote('system:system')};" not in cmd2:
        failures.append(f"explicit owner not stamped literally: {cmd2!r}")
    if "need_dirs=" not in cmd2:
        failures.append(f"explicit owner must still record missing dirs: {cmd2!r}")

    if failures:
        print("FAIL")
        for f in failures:
            print(" -", f)
        return 1
    print("PASS: root_push_file walks ancestors, inherits owner, chowns new dirs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

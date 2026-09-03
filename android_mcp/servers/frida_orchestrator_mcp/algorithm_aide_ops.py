from __future__ import annotations

import json
import posixpath
import shlex
import time
from pathlib import Path
from typing import Dict, List, Optional

from android_mcp.common.process import run_command
from android_mcp.common.adb import adb_args, choose_real_serial

from .adb_ops import _safe_file_name, _work_path, adb_root_shell
from .package_ops import install_apk, list_reverse_apps, package_info, start_app
from .lsposed_ops import lsposed_status
from .root_ops import root_push_file, root_read_file, sqlite_query_root
from .toolchain import ALGORITHM_AIDE_APK, ALGORITHM_AIDE_PACKAGE


"""AlgorithmAide and generic content/intent IPC helpers."""

# AlgorithmAide runs as the system uid and keeps its per-package config under
# /data/system/junge/<pkg>/ owned by system:system (dirs 0700, files 0600).
# root_push_file stamps the *file* owner, but its `mkdir -p` runs through `su`,
# so any freshly-created <pkg>/ or frida/ dir lands root:root and the system-uid
# app can no longer manage (or, under stricter modes, read) its own config.
_JUNGE_ROOT = "/data/system/junge"
_JUNGE_OWNER = "system:system"


def _junge_package(package: str) -> str:
    """Reject path traversal in per-app junge paths (remote path is interpolated)."""
    name = (package or "").strip()
    if not name or "/" in name or "\\" in name or ".." in name:
        raise ValueError(f"invalid junge package name: {package!r}")
    return name


def _fix_junge_dir_owner(serial_chosen: str, remote_path: str, timeout: int = 30) -> Optional[Dict[str, object]]:
    """Re-own every dir between ``remote_path`` and the junge root (exclusive)
    back to system:system 0700, so MCP-written config matches app-created config.
    Returns None when the path has no junge-owned parent dir to fix (e.g. files
    that live directly under the junge root such as AppSwitch.json)."""
    norm = posixpath.normpath(remote_path)
    prefix = _JUNGE_ROOT + "/"
    if not norm.startswith(prefix):
        return None
    dirs: List[str] = []
    cur = posixpath.dirname(norm)
    while cur.startswith(prefix) and cur != _JUNGE_ROOT:
        dirs.append(cur)
        cur = posixpath.dirname(cur)
    if not dirs:
        return None
    quoted = " ".join(shlex.quote(d) for d in dirs)
    cmd = f"chown {shlex.quote(_JUNGE_OWNER)} {quoted} && chmod 700 {quoted}"
    return adb_root_shell(serial_chosen, cmd, timeout=max(10, min(int(timeout), 30)))


def setup_algorithm_aide(serial: Optional[str] = None, apk_path: Optional[str] = None, launch: bool = True) -> Dict[str, object]:
    local = str(Path(apk_path) if apk_path else ALGORITHM_AIDE_APK)
    install = install_apk(serial, local, reinstall=True, grant=True)
    serial_chosen = str(install["serial"])
    appops = []
    for cmd in [
        f"appops set {ALGORITHM_AIDE_PACKAGE} MANAGE_EXTERNAL_STORAGE allow",
        f"appops set {ALGORITHM_AIDE_PACKAGE} SYSTEM_ALERT_WINDOW allow",
        f"pm grant {ALGORITHM_AIDE_PACKAGE} android.permission.READ_EXTERNAL_STORAGE || true",
        f"pm grant {ALGORITHM_AIDE_PACKAGE} android.permission.WRITE_EXTERNAL_STORAGE || true",
    ]:
        appops.append(adb_root_shell(serial_chosen, cmd, timeout=15))
    launch_res = start_app(serial_chosen, ALGORITHM_AIDE_PACKAGE) if launch else None
    return {"serial": serial_chosen, "install": install, "appops": appops, "launch": launch_res, "package_info": package_info(serial_chosen, ALGORITHM_AIDE_PACKAGE)}


def algorithm_aide_status(serial: Optional[str] = None) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    return {
        "serial": serial_chosen,
        "package": package_info(serial_chosen, ALGORITHM_AIDE_PACKAGE),
        "reverse_apps": list_reverse_apps(serial_chosen),
        "prefs": algorithm_aide_list_prefs(serial_chosen),
        "lsposed": lsposed_status(serial_chosen),
    }


def algorithm_aide_list_prefs(serial: Optional[str] = None) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    cmd = f"ls -l /data/user/0/{ALGORITHM_AIDE_PACKAGE}/shared_prefs 2>/dev/null || true"
    res = adb_root_shell(serial_chosen, cmd, timeout=20)
    prefs = []
    for line in str(res["stdout"]).splitlines():
        parts = line.split()
        if len(parts) >= 9 and (parts[-1].endswith(".sp") or parts[-1].endswith(".xml")):
            prefs.append({"name": parts[-1], "size": parts[4], "raw": line})
    return {"serial": serial_chosen, "prefs": prefs, "raw": res}


def algorithm_aide_read_pref(serial: Optional[str], pref_name: str, max_bytes: int = 8192) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    if "/" in pref_name or "\\" in pref_name:
        raise ValueError("pref_name must be a simple file name")
    remote = f"/data/user/0/{ALGORITHM_AIDE_PACKAGE}/shared_prefs/{pref_name}"
    q = shlex.quote(remote)
    cmd = f"if [ -f {q} ]; then xxd -l {max_bytes} -g 1 {q} 2>/dev/null || toybox xxd -l {max_bytes} -g 1 {q} 2>/dev/null || cat {q}; else echo MISSING; fi"
    res = adb_root_shell(serial_chosen, cmd, timeout=30)
    return {"serial": serial_chosen, "pref": pref_name, "remote": remote, "hex_or_text": res}


def content_query(
    serial: Optional[str],
    uri: str,
    projection: Optional[List[str]] = None,
    selection: Optional[str] = None,
    sort: Optional[str] = None,
    timeout: int = 20,
) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    args = adb_args(serial_chosen) + ["shell", "content", "query", "--uri", uri]
    if projection:
        args += ["--projection", ":".join(projection)]
    if selection:
        args += ["--where", selection]
    if sort:
        args += ["--sort", sort]
    res = run_command(args, timeout=timeout)
    return {"serial": serial_chosen, "uri": uri, "projection": projection, "selection": selection, "sort": sort, "result": res}


def content_query_algorithm_aide(serial: Optional[str], uri: str, projection: Optional[List[str]] = None, timeout: int = 20) -> Dict[str, object]:
    return content_query(serial, uri, projection=projection, timeout=timeout)


def _string_binds(values: Dict[str, object]) -> List[str]:
    binds: List[str] = []
    for key, raw_value in values.items():
        value = raw_value if raw_value is not None else ""
        binds += ["--bind", f"{key}:s:{value}"]
    return binds


def content_insert(serial: Optional[str], uri: str, values: Dict[str, str], timeout: int = 20) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    args = adb_args(serial_chosen) + ["shell", "content", "insert", "--uri", uri]
    args += _string_binds(values)
    res = run_command(args, timeout=timeout)
    return {"serial": serial_chosen, "uri": uri, "values": values, "result": res}


def content_update(serial: Optional[str], uri: str, values: Dict[str, str], where: Optional[str] = None, timeout: int = 20) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    args = adb_args(serial_chosen) + ["shell", "content", "update", "--uri", uri]
    args += _string_binds(values)
    if where:
        args += ["--where", where]
    res = run_command(args, timeout=timeout)
    return {"serial": serial_chosen, "uri": uri, "values": values, "where": where, "result": res}


def content_delete(serial: Optional[str], uri: str, where: Optional[str] = None, timeout: int = 20) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    args = adb_args(serial_chosen) + ["shell", "content", "delete", "--uri", uri]
    if where:
        args += ["--where", where]
    res = run_command(args, timeout=timeout)
    return {"serial": serial_chosen, "uri": uri, "where": where, "result": res}


def content_call(serial: Optional[str], uri: str, method: str, arg: Optional[str] = None, extras: Optional[Dict[str, str]] = None, timeout: int = 20) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    args = adb_args(serial_chosen) + ["shell", "content", "call", "--uri", uri, "--method", method]
    if arg is not None:
        args += ["--arg", arg]
    for key, value in (extras or {}).items():
        args += ["--extra", f"{key}:s:{value}"]
    res = run_command(args, timeout=timeout)
    return {"serial": serial_chosen, "uri": uri, "method": method, "arg": arg, "extras": extras or {}, "result": res}


def _append_intent_args(
    args: List[str],
    *,
    component: Optional[str] = None,
    package: Optional[str] = None,
    action: Optional[str] = None,
    data_uri: Optional[str] = None,
    mime_type: Optional[str] = None,
    categories: Optional[List[str]] = None,
    extras: Optional[Dict[str, str]] = None,
    flags: Optional[List[str]] = None,
) -> List[str]:
    if component:
        args += ["-n", component]
    if package:
        args += ["-p", package]
    if action:
        args += ["-a", action]
    if data_uri:
        args += ["-d", data_uri]
    if mime_type:
        args += ["-t", mime_type]
    for category in categories or []:
        args += ["-c", category]
    for flag in flags or []:
        args += ["-f", str(flag)]
    for key, value in (extras or {}).items():
        args += ["--es", key, str(value)]
    return args


def intent_start_activity(
    serial: Optional[str],
    component: Optional[str] = None,
    package: Optional[str] = None,
    action: Optional[str] = None,
    data_uri: Optional[str] = None,
    mime_type: Optional[str] = None,
    categories: Optional[List[str]] = None,
    extras: Optional[Dict[str, str]] = None,
    flags: Optional[List[str]] = None,
    wait: bool = False,
    timeout: int = 20,
) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    args = adb_args(serial_chosen) + ["shell", "am", "start"]
    if wait:
        args.append("-W")
    args = _append_intent_args(
        args,
        component=component,
        package=package,
        action=action,
        data_uri=data_uri,
        mime_type=mime_type,
        categories=categories,
        extras=extras,
        flags=flags,
    )
    res = run_command(args, timeout=timeout)
    return {"serial": serial_chosen, "kind": "activity", "component": component, "package": package, "action": action, "data_uri": data_uri, "extras": extras or {}, "result": res}


def intent_broadcast(
    serial: Optional[str],
    action: str,
    component: Optional[str] = None,
    package: Optional[str] = None,
    data_uri: Optional[str] = None,
    extras: Optional[Dict[str, str]] = None,
    receiver_permission: Optional[str] = None,
    timeout: int = 20,
) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    args = adb_args(serial_chosen) + ["shell", "am", "broadcast"]
    args = _append_intent_args(args, component=component, package=package, action=action, data_uri=data_uri, extras=extras)
    if receiver_permission:
        args += ["--receiver-permission", receiver_permission]
    res = run_command(args, timeout=timeout)
    return {"serial": serial_chosen, "kind": "broadcast", "component": component, "package": package, "action": action, "data_uri": data_uri, "extras": extras or {}, "result": res}


def intent_start_service(
    serial: Optional[str],
    component: Optional[str] = None,
    package: Optional[str] = None,
    action: Optional[str] = None,
    data_uri: Optional[str] = None,
    extras: Optional[Dict[str, str]] = None,
    foreground: bool = False,
    timeout: int = 20,
) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    subcmd = "start-foreground-service" if foreground else "startservice"
    args = adb_args(serial_chosen) + ["shell", "am", subcmd]
    args = _append_intent_args(args, component=component, package=package, action=action, data_uri=data_uri, extras=extras)
    res = run_command(args, timeout=timeout)
    return {"serial": serial_chosen, "kind": "service", "foreground": foreground, "component": component, "package": package, "action": action, "result": res}


def intent_stop_service(serial: Optional[str], component: str, timeout: int = 20) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    res = run_command(adb_args(serial_chosen) + ["shell", "am", "stopservice", "-n", component], timeout=timeout)
    return {"serial": serial_chosen, "kind": "service_stop", "component": component, "result": res}


def algorithm_aide_query_config(serial: Optional[str], pref: str, keys: List[str], timeout: int = 20) -> Dict[str, object]:
    # ConfigProvider reads SharedPreferences from content://algorithmAidePro/<pref>
    return content_query_algorithm_aide(serial, f"content://algorithmAidePro/{pref}", keys, timeout)


def algorithm_aide_put_config(serial: Optional[str], pref: str, values: Dict[str, str], timeout: int = 20) -> Dict[str, object]:
    # ConfigProvider.insert iterates ContentValues and writes strings to SharedPreferences for the URI path segment.
    return content_insert(serial, f"content://algorithmAidePro/{pref}", values, timeout)


def algorithm_aide_read_json(serial: Optional[str], package: str, source: str = "system", timeout: int = 30) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    if source == "sdcard":
        remote = f"/sdcard/Android/data/{ALGORITHM_AIDE_PACKAGE}/files/config/{_junge_package(package)}.json"
    elif source == "appswitch":
        remote = "/data/system/junge/AppSwitch.json"
    elif source == "loglist":
        remote = "/data/system/junge/logList.json"
    else:
        remote = f"/data/system/junge/{_junge_package(package)}/config.json"
    read = root_read_file(serial_chosen, remote, max_bytes=1048576, mode="text", timeout=timeout)
    parsed = None
    try:
        parsed = json.loads(str(read["result"]["stdout"]))
    except Exception:
        parsed = None
    return {"serial": serial_chosen, "package": package, "source": source, "remote": remote, "json": parsed, "read": read}


def algorithm_aide_write_json(
    serial: Optional[str],
    package: str,
    config: Dict[str, object],
    mirror_sdcard: bool = True,
    timeout: int = 60,
) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    package = _junge_package(package)
    content = json.dumps(config, ensure_ascii=False, separators=(",", ":"))
    local_dir = _work_path("algorithm_aide")
    local = local_dir / f"{_safe_file_name(package)}_{int(time.time())}.json"
    local.write_text(content, encoding="utf-8")
    system_remote = f"/data/system/junge/{package}/config.json"
    writes = [root_push_file(serial_chosen, str(local), system_remote, mode="600", owner=_JUNGE_OWNER, timeout=timeout)]
    dir_fix = _fix_junge_dir_owner(serial_chosen, system_remote, timeout=timeout)
    if mirror_sdcard:
        sd_remote = f"/sdcard/Android/data/{ALGORITHM_AIDE_PACKAGE}/files/config/{package}.json"
        writes.append(root_push_file(serial_chosen, str(local), sd_remote, mode="660", timeout=timeout))
    return {"serial": serial_chosen, "package": package, "config": config, "local": str(local), "writes": writes, "dir_fix": dir_fix, "verify": algorithm_aide_read_json(serial_chosen, package, "system", timeout=timeout)}


def algorithm_aide_set_appswitch(serial: Optional[str], package: str, enabled: bool, timeout: int = 60) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    package = _junge_package(package)
    current = algorithm_aide_read_json(serial_chosen, package, "appswitch", timeout=timeout)
    data = current.get("json") if isinstance(current.get("json"), dict) else {}
    data[str(package)] = bool(enabled)
    local_dir = _work_path("algorithm_aide")
    local = local_dir / f"AppSwitch_{int(time.time())}.json"
    local.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    write = root_push_file(serial_chosen, str(local), "/data/system/junge/AppSwitch.json", mode="600", owner=_JUNGE_OWNER, timeout=timeout)
    return {"serial": serial_chosen, "package": package, "enabled": enabled, "before": current, "write": write, "after": algorithm_aide_read_json(serial_chosen, package, "appswitch", timeout=timeout)}


def algorithm_aide_write_frida_script(serial: Optional[str], package: str, name: str, script: str, timeout: int = 60) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    package = _junge_package(package)
    safe_name = _safe_file_name(name if name.endswith(".js") else f"{name}.js", "script.js")
    local_dir = _work_path("algorithm_aide", "frida_scripts")
    local = local_dir / f"{_safe_file_name(package)}_{safe_name}"
    local.write_text(script, encoding="utf-8")
    remote = f"/data/system/junge/{package}/frida/{safe_name}"
    write = root_push_file(serial_chosen, str(local), remote, mode="600", owner=_JUNGE_OWNER, timeout=timeout)
    dir_fix = _fix_junge_dir_owner(serial_chosen, remote, timeout=timeout)
    return {"serial": serial_chosen, "package": package, "name": safe_name, "local": str(local), "remote": remote, "write": write, "dir_fix": dir_fix}


def algorithm_aide_log_db_query(
    serial: Optional[str],
    package: str,
    sql: str = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
    max_rows: int = 200,
    timeout: int = 120,
) -> Dict[str, object]:
    db_path = f"/sdcard/Android/media/{_junge_package(package)}/database/algorithmAidePro.db"
    return sqlite_query_root(serial, db_path, sql, max_rows=max_rows, timeout=timeout)

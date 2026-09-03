from __future__ import annotations

import hashlib
import os
import re
import shlex
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional

from android_mcp.common.paths import project_root, safe_output_path
from android_mcp.common.process import run_command
from android_mcp.common.adb import adb_args, choose_real_serial, list_devices



"""ADB, IPC fallback, UI fallback and network helpers."""

def _work_path(*parts: str) -> Path:
    path = project_root() / "android_mcp" / "_work"
    for part in parts:
        path = path / part
    path.mkdir(parents=True, exist_ok=True)
    return path


def _optional_local_dir(output_dir: Optional[str], default: Path) -> Path:
    if output_dir:
        out = Path(output_dir)
        if not out.is_absolute():
            out = project_root() / out
    else:
        out = default
    out = out.resolve()
    project = project_root().resolve()
    project_s = str(project).lower()
    out_s = str(out).lower()
    if out != project and not out_s.startswith(project_s + os.sep.lower()):
        raise ValueError(f"output_dir must stay under project root: {out}")
    out.mkdir(parents=True, exist_ok=True)
    return out


def _safe_file_name(value: str, default: str = "artifact") -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return name.strip("._") or default


def _hash_suffix(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:12]


def _q(remote_path: str) -> str:
    return shlex.quote(remote_path)


def _first_match(text: str, pattern: str) -> Optional[str]:
    m = re.search(pattern, text)
    return m.group(1) if m else None


def adb_devices(real_only: bool = True) -> Dict[str, object]:
    return {"devices": list_devices(real_only=real_only)}


def adb_shell(serial: Optional[str], command: str, timeout: int = 20) -> Dict[str, object]:
    args = adb_args(serial) + ["shell", command]
    return run_command(args, timeout=timeout)


def adb_root_shell(serial: Optional[str], command: str, timeout: int = 20) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    # adb joins shell arguments on-device; quote the whole root command so
    # constructs like `if ...; then ...; fi` are consumed by su -c, not by the
    # intermediate shell. shlex.quote is POSIX-target quoting, not host-shell quoting.
    args = adb_args(serial_chosen) + ["shell", f"su -c {shlex.quote(command)}"]
    result = run_command(args, timeout=timeout)
    result["serial"] = serial_chosen
    return result


def device_health(serial: Optional[str] = None) -> Dict[str, object]:
    from .frida_ops import patched_frida_status

    serial_chosen = choose_real_serial(serial)
    # Batch getprop into one shell to cut round-trips (and stall amplification).
    prop_keys = [
        "ro.product.model",
        "ro.product.cpu.abi",
        "ro.build.version.release",
        "ro.build.version.sdk",
    ]
    prop_cmd = " ; ".join([f"echo {k}=$(getprop {k})" for k in prop_keys])
    prop_res = run_command(adb_args(serial_chosen) + ["shell", prop_cmd], timeout=10)
    props: Dict[str, str] = {}
    for line in str(prop_res.get("stdout") or "").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            if key in prop_keys:
                props[key] = value.strip()
    for key in prop_keys:
        props.setdefault(key, "")
    shell_id = run_command(adb_args(serial_chosen) + ["shell", "id"], timeout=10)
    root_id = adb_root_shell(serial_chosen, "id", timeout=10)
    frida_status = patched_frida_status(serial_chosen)
    return {
        "serial": serial_chosen,
        "props": props,
        "shell_id": shell_id["stdout"],
        "root_id": root_id["stdout"],
        "root_ok": root_id["returncode"] == 0 and "uid=0" in str(root_id["stdout"]),
        "frida": frida_status,
        "timed_out": bool(prop_res.get("timed_out") or shell_id.get("timed_out") or root_id.get("timed_out")),
    }


def current_app(serial: Optional[str] = None) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    # Android 12+ dropped the focus lines from `dumpsys window windows`; `dumpsys window`
    # still carries mCurrentFocus / mFocusedApp. Fall back to the old subcommand if empty.
    result = run_command(adb_args(serial_chosen) + ["shell", "dumpsys", "window"], timeout=15)
    text = str(result["stdout"])
    focus = ""
    focused_app = ""
    for line in text.splitlines():
        stripped = line.strip()
        if not focus and "mCurrentFocus" in stripped:
            focus = stripped
        elif not focused_app and "mFocusedApp" in stripped:
            focused_app = stripped
        if focus and focused_app:
            break
    return {
        "serial": serial_chosen,
        "focus": focus,
        "focused_app": focused_app,
        "raw_returncode": result["returncode"],
        "stderr": result["stderr"],
    }


def reqable_status(serial: Optional[str] = None) -> Dict[str, object]:
    from .package_ops import package_info
    from .root_ops import root_ls

    serial_chosen = choose_real_serial(serial)
    package = "com.reqable.android"
    return {
        "serial": serial_chosen,
        "package": package,
        "info": package_info(serial_chosen, package),
        "proxy": run_command(adb_args(serial_chosen) + ["shell", "settings", "get", "global", "http_proxy"], timeout=15),
        "vpn": run_command(adb_args(serial_chosen) + ["shell", "dumpsys", "connectivity"], timeout=30),
        "data_files": root_ls(serial_chosen, f"/data/user/0/{package}", long=True, timeout=20),
    }


def android_proxy_set(serial: Optional[str], host: str, port: int, timeout: int = 20) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    value = f"{host}:{int(port)}"
    res = run_command(adb_args(serial_chosen) + ["shell", "settings", "put", "global", "http_proxy", value], timeout=timeout)
    return {"serial": serial_chosen, "proxy": value, "result": res}


def android_proxy_clear(serial: Optional[str] = None, timeout: int = 20) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    res1 = run_command(adb_args(serial_chosen) + ["shell", "settings", "put", "global", "http_proxy", ":0"], timeout=timeout)
    res2 = run_command(adb_args(serial_chosen) + ["shell", "settings", "delete", "global", "http_proxy"], timeout=timeout)
    return {"serial": serial_chosen, "put": res1, "delete": res2}


def screenshot_save(serial: Optional[str] = None, output: Optional[str] = None) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    base = project_root() / "android_mcp" / "_work" / "screenshots"
    out = safe_output_path(base, output, f"screen_{int(time.time())}.png")
    remote = f"/data/local/tmp/{out.name}"
    cap = run_command(adb_args(serial_chosen) + ["shell", "screencap", "-p", remote], timeout=30)
    pull = run_command(adb_args(serial_chosen) + ["pull", remote, str(out)], timeout=60)
    cleanup = run_command(adb_args(serial_chosen) + ["shell", "rm", "-f", remote], timeout=10)
    return {"serial": serial_chosen, "local_path": str(out), "capture": cap, "pull": pull, "cleanup": cleanup}


def ui_dump(serial: Optional[str] = None, output: Optional[str] = None) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    base = project_root() / "android_mcp" / "_work" / "ui"
    out = safe_output_path(base, output, f"ui_{int(time.time())}.xml")
    remote = "/data/local/tmp/window_dump.xml"
    dump = run_command(adb_args(serial_chosen) + ["shell", "uiautomator", "dump", remote], timeout=30)
    pull = run_command(adb_args(serial_chosen) + ["pull", remote, str(out)], timeout=60)
    cleanup = run_command(adb_args(serial_chosen) + ["shell", "rm", "-f", remote], timeout=10)
    clickable = []
    if out.exists() and out.stat().st_size > 0:
        try:
            root = ET.parse(out).getroot()
            for node in root.iter("node"):
                if node.attrib.get("clickable") == "true" or node.attrib.get("text") or node.attrib.get("content-desc"):
                    clickable.append({k: node.attrib.get(k, "") for k in ["text", "resource-id", "class", "package", "content-desc", "clickable", "bounds"]})
        except Exception:
            pass
    return {"serial": serial_chosen, "local_path": str(out), "dump": dump, "pull": pull, "cleanup": cleanup, "nodes": clickable[:300]}


def tap(serial: Optional[str], x: int, y: int) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    res = run_command(adb_args(serial_chosen) + ["shell", "input", "tap", str(x), str(y)], timeout=10)
    return {"serial": serial_chosen, "result": res}


def swipe(serial: Optional[str], x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    res = run_command(adb_args(serial_chosen) + ["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)], timeout=15)
    return {"serial": serial_chosen, "result": res}


def input_text(serial: Optional[str], text: str) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    # `adb shell input text` runs through the device shell, so quote the whole
    # argument to keep metacharacters (; & $ quotes ...) literal; %s is how the
    # `input` binary represents a space inside a single argument.
    escaped = shlex.quote(text.replace(" ", "%s"))
    res = run_command(adb_args(serial_chosen) + ["shell", "input", "text", escaped], timeout=20)
    return {"serial": serial_chosen, "result": res}


def press_key(serial: Optional[str], key: str) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    res = run_command(adb_args(serial_chosen) + ["shell", "input", "keyevent", key], timeout=10)
    return {"serial": serial_chosen, "result": res}


def logcat_tail(serial: Optional[str] = None, package: Optional[str] = None, lines: int = 200) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    cmd = f"logcat -d -t {lines}"
    if package:
        pid_res = run_command(adb_args(serial_chosen) + ["shell", "pidof", package], timeout=10)
        pid = str(pid_res["stdout"]).strip().split()
        if pid:
            cmd += f" --pid {pid[0]}"
    res = run_command(adb_args(serial_chosen) + ["shell", cmd], timeout=30)
    return {"serial": serial_chosen, "package": package, "result": res}


def adb_forward(serial: Optional[str], local: str, remote: str, remove: bool = False, timeout: int = 20) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    args = adb_args(serial_chosen) + ["forward"]
    if remove:
        args += ["--remove", local]
    else:
        args += [local, remote]
    res = run_command(args, timeout=timeout)
    return {"serial": serial_chosen, "local": local, "remote": remote, "remove": remove, "result": res}


def adb_reverse(serial: Optional[str], remote: str, local: str, remove: bool = False, timeout: int = 20) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    args = adb_args(serial_chosen) + ["reverse"]
    if remove:
        args += ["--remove", remote]
    else:
        args += [remote, local]
    res = run_command(args, timeout=timeout)
    return {"serial": serial_chosen, "remote": remote, "local": local, "remove": remove, "result": res}


def tcp_probe_device(serial: Optional[str], host: str = "127.0.0.1", ports: Optional[List[int]] = None, timeout: int = 30) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    probe_ports = ports or [8000, 8080, 8888, 9999, 27042, 27043]
    results = []
    open_ports = []
    for port in probe_ports:
        port_int = int(port)
        cmd = f"(toybox nc -z -w 1 {shlex.quote(host)} {port_int} >/dev/null 2>&1 || nc -z -w 1 {shlex.quote(host)} {port_int} >/dev/null 2>&1) && echo OPEN || echo CLOSED"
        res = run_command(adb_args(serial_chosen) + ["shell", cmd], timeout=max(5, min(timeout, 30)))
        is_open = "OPEN" in str(res["stdout"])
        if is_open:
            open_ports.append(port_int)
        results.append({"port": port_int, "open": is_open, "result": res})
    return {"serial": serial_chosen, "host": host, "open_ports": open_ports, "results": results}


def http_probe_forwarded(url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None, body: Optional[str] = None, timeout: int = 10) -> Dict[str, object]:
    from urllib import request as urlrequest
    from urllib.error import HTTPError, URLError

    data = body.encode("utf-8") if body is not None else None
    req = urlrequest.Request(url, data=data, method=(method or "GET").upper())
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            content = resp.read(65536)
            return {
                "url": url,
                "method": req.get_method(),
                "ok": 200 <= resp.status < 400,
                "status_code": resp.status,
                "headers": dict(resp.headers.items()),
                "text_excerpt": content.decode("utf-8", errors="replace"),
            }
    except HTTPError as exc:
        content = exc.read(65536)
        return {"url": url, "method": req.get_method(), "ok": False, "status_code": exc.code, "headers": dict(exc.headers.items()), "text_excerpt": content.decode("utf-8", errors="replace")}
    except URLError as exc:
        return {"url": url, "method": req.get_method(), "ok": False, "error": str(exc)}

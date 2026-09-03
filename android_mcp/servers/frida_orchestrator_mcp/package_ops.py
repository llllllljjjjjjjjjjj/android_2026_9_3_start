from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from android_mcp.common.paths import project_root, resolve_under_root, toolchain_root
from android_mcp.common.process import run_command
from android_mcp.common.adb import adb_args, choose_real_serial

from .adb_ops import _first_match, _hash_suffix, _optional_local_dir, _q, _safe_file_name, _work_path, adb_root_shell


"""Installed package and pulled APK helpers."""

def start_app(serial: Optional[str], package: str, activity: Optional[str] = None) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    if activity:
        cmd = ["shell", "am", "start", "-n", f"{package}/{activity}"]
    else:
        cmd = ["shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"]
    result = run_command(adb_args(serial_chosen) + cmd, timeout=20)
    result["serial"] = serial_chosen
    return result


def stop_app(serial: Optional[str], package: str) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    result = run_command(adb_args(serial_chosen) + ["shell", "am", "force-stop", package], timeout=15)
    result["serial"] = serial_chosen
    return result


def clear_app(serial: Optional[str], package: str) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    result = run_command(adb_args(serial_chosen) + ["shell", "pm", "clear", package], timeout=20)
    result["serial"] = serial_chosen
    return result


def install_apk(serial: Optional[str], apk_path: str, reinstall: bool = True, grant: bool = True) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    local = Path(apk_path)
    if not local.is_absolute():
        local = resolve_under_root(apk_path)
    if not local.exists():
        raise ValueError(f"apk not found: {apk_path}")
    args = adb_args(serial_chosen) + ["install"]
    if reinstall:
        args.append("-r")
    if grant:
        args.append("-g")
    args.append(str(local))
    result = run_command(args, timeout=180)
    result["serial"] = serial_chosen
    result["apk"] = str(local)
    return result


def package_info(serial: Optional[str], package: str) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    path_res = run_command(adb_args(serial_chosen) + ["shell", "pm", "path", package], timeout=15)
    dump_res = run_command(adb_args(serial_chosen) + ["shell", "dumpsys", "package", package], timeout=30)
    dump = str(dump_res["stdout"])
    version_name = _first_match(dump, r"versionName=([^\s]+)")
    version_code = _first_match(dump, r"versionCode=(\d+)")
    providers = re.findall(r"\[([^\]]+)\]:\s*\n\s*Provider\{[^\n]+", dump)
    return {
        "serial": serial_chosen,
        "package": package,
        "installed": path_res["returncode"] == 0 and "package:" in str(path_res["stdout"]),
        "path": str(path_res["stdout"]).strip(),
        "version_name": version_name,
        "version_code": version_code,
        "providers": providers,
        "dump_excerpt": "\n".join([line for line in dump.splitlines() if any(k in line.lower() for k in ["version", "provider", "permission", "datadir"] )][:120]),
    }


def pull_package_apk(serial: Optional[str], package: str, output_dir: Optional[str] = None, timeout: int = 180) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    base_dir = _optional_local_dir(output_dir, _work_path("device_apks") / package)
    pm_path = run_command(adb_args(serial_chosen) + ["shell", "pm", "path", package], timeout=30)
    remote_paths = []
    for raw in str(pm_path["stdout"]).splitlines():
        line = raw.strip()
        if line.startswith("package:"):
            remote_paths.append(line[len("package:") :])
    pulled = []
    for idx, remote in enumerate(remote_paths):
        leaf = Path(remote).name or f"base_{idx}.apk"
        local = base_dir / leaf
        pull = run_command(adb_args(serial_chosen) + ["pull", remote, str(local)], timeout=timeout)
        fallback = None
        if pull["returncode"] != 0 or not local.exists():
            tmp = f"/data/local/tmp/{_safe_file_name(package)}_{idx}_{_hash_suffix(remote)}.apk"
            copy = adb_root_shell(serial_chosen, f"cp -f {_q(remote)} {_q(tmp)} && chmod 644 {_q(tmp)}", timeout=60)
            pull = run_command(adb_args(serial_chosen) + ["pull", tmp, str(local)], timeout=timeout)
            cleanup = adb_root_shell(serial_chosen, f"rm -f {_q(tmp)}", timeout=15)
            fallback = {"copy": copy, "cleanup": cleanup, "tmp": tmp}
        size = local.stat().st_size if local.exists() else 0
        sha256 = None
        if local.exists() and size > 0:
            sha256 = hashlib.sha256(local.read_bytes()).hexdigest()
        pulled.append({"remote": remote, "local": str(local), "size": size, "sha256": sha256, "pull": pull, "fallback": fallback})
    return {"serial": serial_chosen, "package": package, "local_dir": str(base_dir), "remote_paths": remote_paths, "pm_path": pm_path, "files": pulled}


def _has_analysis_sources(root_dir: Path) -> bool:
    if not root_dir.exists():
        return False
    for path in root_dir.rglob("*.apk"):
        if path.is_file():
            return True
    for path in root_dir.rglob("AndroidManifest.xml"):
        if path.is_file():
            return True
    return False


def _default_analysis_root(default_root: Path) -> Path:
    if _has_analysis_sources(default_root):
        return default_root
    bundled = toolchain_root() / "apks" / "device-tools"
    if _has_analysis_sources(bundled):
        return bundled
    return default_root


def _analysis_summary(out_path: Path) -> Optional[Dict[str, object]]:
    if not out_path.exists():
        return None
    try:
        data = json.loads(out_path.read_text(encoding="utf-8", errors="replace"))
        return {
            "package_count": data.get("package_count"),
            "packages": [
                {
                    "package": p.get("package"),
                    "authorities": p.get("authorities", []),
                    "xposed": bool(p.get("xposed_meta")),
                    "components": {k: len(v or []) for k, v in (p.get("components") or {}).items()},
                    "warnings": p.get("warnings", [])[:3],
                }
                for p in data.get("packages", [])
            ],
        }
    except Exception as exc:
        return {"error": str(exc)}


def analyze_pulled_apks(root: Optional[str] = None, output: Optional[str] = None, pretty: bool = True, timeout: int = 180) -> Dict[str, object]:
    script = project_root() / "android_mcp" / "tools" / "analyze_device_apks.py"
    if not script.exists():
        raise ValueError(f"analyze_device_apks.py not found: {script}")
    output_root = project_root() / "android_mcp" / "_work" / "device_apks"
    root_dir = Path(root) if root else output_root
    if not root_dir.is_absolute():
        root_dir = project_root() / root_dir
    analysis_root = root_dir if root else _default_analysis_root(root_dir)
    out_path = None
    if output:
        out_path = Path(output)
        if not out_path.is_absolute():
            out_path = output_root / out_path
    else:
        out_path = output_root / "analysis_manifest.json"

    if root is None and analysis_root != root_dir and out_path.exists() and not output:
        summary = _analysis_summary(out_path)
        return {
            "root": str(root_dir),
            "output": str(out_path),
            "cached": True,
            "note": "No APK or decoded manifest remains in android_mcp/_work/device_apks after cleanup; returning the cached manifest. Pass root=android_mcp/toolchain/apks/device-tools or pull APKs again to refresh.",
            "result": {"returncode": 0, "stdout": "cached analysis_manifest.json", "stderr": ""},
            "summary": summary,
        }

    args = [sys.executable, str(script), "--root", str(analysis_root), "--output", str(out_path)]
    if pretty:
        args.append("--pretty")
    result = run_command(args, timeout=timeout, cwd=project_root())
    summary = _analysis_summary(out_path)
    return {"root": str(analysis_root), "output": str(out_path), "cached": False, "result": result, "summary": summary}


def _load_manifest_record(package: str) -> Optional[Dict[str, Any]]:
    path = project_root() / "android_mcp" / "_work" / "device_apks" / "analysis_manifest.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None
    for record in data.get("packages", []):
        if record.get("package") == package:
            return record
    return None


def package_components(serial: Optional[str], package: str, include_dump: bool = False, timeout: int = 30) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    manifest = _load_manifest_record(package)
    dump = run_command(adb_args(serial_chosen) + ["shell", "dumpsys", "package", package], timeout=timeout)
    dump_text = str(dump["stdout"])
    if manifest:
        result: Dict[str, object] = {
            "serial": serial_chosen,
            "package": package,
            "source": "analysis_manifest.json",
            "components": manifest.get("components", {}),
            "authorities": manifest.get("authorities", []),
            "exported": manifest.get("exported", []),
            "intent_actions": manifest.get("intent_actions", []),
            "data_schemes": manifest.get("data_schemes", []),
            "xposed_meta": manifest.get("xposed_meta", []),
            "warnings": manifest.get("warnings", []),
            "dumpsys_returncode": dump["returncode"],
            "dumpsys_stderr": dump["stderr"],
        }
    else:
        result = {
            "serial": serial_chosen,
            "package": package,
            "source": "dumpsys_excerpt",
            "providers": re.findall(r"authority=([^\s]+)", dump_text),
            "actions": sorted(set(re.findall(r"Action: \"([^\"]+)\"", dump_text))),
            "dumpsys_returncode": dump["returncode"],
            "dumpsys_stderr": dump["stderr"],
        }
    if include_dump:
        result["dump"] = dump_text
    else:
        result["raw_excerpt"] = "\n".join(dump_text.splitlines()[:220])
    return result


def list_reverse_apps(serial: Optional[str] = None) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    res = run_command(adb_args(serial_chosen) + ["shell", "pm", "list", "packages", "-3"], timeout=30)
    keywords = ["junge", "algorithm", "lsposed", "xposed", "reqable", "trust", "magisk", "shizuku", "topactivity", "hidemy", "hook", "proxy", "termux", "mt", "apk", "debug", "xhs"]
    packages = []
    for line in str(res["stdout"]).splitlines():
        pkg = line.replace("package:", "").strip()
        lower = pkg.lower()
        if any(k in lower for k in keywords):
            packages.append(pkg)
    return {"serial": serial_chosen, "packages": sorted(packages), "raw_returncode": res["returncode"], "stderr": res["stderr"]}

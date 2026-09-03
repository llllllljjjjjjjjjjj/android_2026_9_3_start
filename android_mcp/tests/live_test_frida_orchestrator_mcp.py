from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "android_mcp" / "servers" / "frida_orchestrator_mcp" / "server.py"
REPORT_DIR = ROOT / "android_mcp" / "_work" / "test_reports"
PY = sys.executable


def default_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("ANDROID_MCP_PROJECT_ROOT", str(ROOT))
    env.setdefault("ANDROID_MCP_ALLOW_EMULATOR", "0")
    env.setdefault("ANDROID_MCP_REMOTE_PATCHED_FRIDA", "/data/local/tmp/new-server")
    # Do not pin old machine-specific paths here. frida-orchestrator-mcp now
    # resolves adb, AlgorithmAide APK and patched frida-server from
    # android_mcp/toolchain by default.
    return env


def _truncate(value: Any, limit: int = 2400) -> Any:
    if isinstance(value, str):
        if len(value) > limit:
            return value[:limit] + f"...<truncated {len(value) - limit} chars>"
        return value
    if isinstance(value, list):
        return [_truncate(item, limit) for item in value[:40]]
    if isinstance(value, dict):
        return {str(k): _truncate(v, limit) for k, v in value.items()}
    return value


def mcp_call(tool: str, arguments: dict[str, Any] | None = None, timeout: int = 120) -> dict[str, Any]:
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": tool, "arguments": arguments or {}}},
    ]
    payload = "\n".join(json.dumps(req, ensure_ascii=False) for req in requests) + "\n"
    proc = subprocess.run(
        [PY, str(SERVER)],
        input=payload,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(ROOT),
        env=default_env(),
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"MCP server exited {proc.returncode}: {proc.stderr}")
    responses = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    call_resp = next((resp for resp in responses if resp.get("id") == 2), None)
    if call_resp is None:
        raise RuntimeError(f"No tools/call response. stdout={proc.stdout!r} stderr={proc.stderr!r}")
    if "error" in call_resp:
        raise RuntimeError(json.dumps(call_resp["error"], ensure_ascii=False))
    text = call_resp["result"]["content"][0]["text"]
    return json.loads(text)


def has_component(record: dict[str, Any], bucket: str, needle: str) -> bool:
    components = record.get("components", {}).get(bucket, [])
    return any(needle in str(item.get("name", "")) or needle in str(item.get("authorities", "")) for item in components)


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_case(
    results: list[dict[str, Any]],
    name: str,
    tool: str,
    args: dict[str, Any] | None,
    validator: Callable[[dict[str, Any]], None],
    timeout: int = 120,
    required: bool = True,
) -> dict[str, Any] | None:
    started = time.time()
    print(f"[RUN] {name} -> {tool}")
    try:
        data = mcp_call(tool, args, timeout=timeout)
        validator(data)
        item = {
            "name": name,
            "tool": tool,
            "required": required,
            "ok": True,
            "elapsed_sec": round(time.time() - started, 3),
            "data": _truncate(data),
        }
        print(f"[ OK] {name}")
        results.append(item)
        return data
    except Exception as exc:  # noqa: BLE001 - test runner boundary
        item = {
            "name": name,
            "tool": tool,
            "required": required,
            "ok": False,
            "elapsed_sec": round(time.time() - started, 3),
            "error": repr(exc),
        }
        print(f"[FAIL] {name}: {exc}")
        results.append(item)
        if required:
            raise
        return None


def main() -> int:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    results: list[dict[str, Any]] = []
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    def validate_devices(data: dict[str, Any]) -> None:
        devices = data.get("devices") or []
        expect(bool(devices), "no real devices returned")
        expect(any(dev.get("is_real") for dev in devices), "no device classified as real")

    run_case(results, "real_device_list", "adb_devices", {"real_only": True}, validate_devices, timeout=60)

    run_case(
        results,
        "device_health_root_frida",
        "device_health",
        {},
        lambda d: expect(bool(d.get("root_ok")), "root_ok is false"),
        timeout=120,
    )

    run_case(
        results,
        "pull_topactivity_apk",
        "pull_package_apk",
        {"package": "com.willme.topactivity", "output_dir": "android_mcp/_work/live_test_pull/com.willme.topactivity", "timeout": 180},
        lambda d: expect(any((f.get("size") or 0) > 0 for f in d.get("files", [])), "no APK pulled"),
        timeout=240,
    )

    run_case(
        results,
        "algorithm_aide_components",
        "package_components",
        {"package": "com.junge.algorithmAidePro", "timeout": 40},
        lambda d: expect(has_component(d, "providers", "algorithmAidePro"), "AlgorithmAidePro provider not detected"),
        timeout=120,
    )

    run_case(
        results,
        "reqable_vpn_component",
        "package_components",
        {"package": "com.reqable.android", "timeout": 40},
        lambda d: expect(has_component(d, "services", "NetbareVpnService"), "Reqable VPN service not detected"),
        timeout=120,
    )

    run_case(
        results,
        "algorithm_aide_content_provider_query",
        "content_query",
        {"uri": "content://algorithmAidePro/com.junge.algorithmAidePro", "projection": ["accept", "startNum"], "timeout": 30},
        lambda d: expect(d.get("result", {}).get("returncode") == 0 and "Row:" in str(d.get("result", {}).get("stdout", "")), "content query did not return a row"),
        timeout=120,
    )

    run_case(
        results,
        "algorithm_aide_read_target_json",
        "algorithm_aide_read_json",
        {"package": "com.xingin.xhs", "source": "system", "timeout": 60},
        lambda d: expect(isinstance(d.get("json"), dict) and bool(d.get("json")), "AlgorithmAide target JSON not parsed"),
        timeout=120,
    )

    # Regression guard: these AlgorithmAide tools live in algorithm_aide_ops.py and call
    # adb_root_shell / list_reverse_apps / lsposed_status. Those names must be imported in
    # that module or every call raises NameError even though the module imports fine.
    # The structural smoke tests (tools/list) cannot catch this; only a real call does.
    run_case(
        results,
        "algorithm_aide_list_prefs",
        "algorithm_aide_list_prefs",
        {},
        lambda d: expect(d.get("raw", {}).get("returncode") == 0, "algorithm_aide_list_prefs did not reach the device (adb_root_shell wiring)"),
        timeout=60,
    )

    run_case(
        results,
        "algorithm_aide_status",
        "algorithm_aide_status",
        {},
        lambda d: expect("reverse_apps" in d and "lsposed" in d, "algorithm_aide_status missing reverse_apps/lsposed (list_reverse_apps/lsposed_status wiring)"),
        timeout=120,
    )

    run_case(
        results,
        "algorithm_aide_read_pref",
        "algorithm_aide_read_pref",
        {"pref_name": "com.junge.algorithmAidePro_preferences.xml", "max_bytes": 256},
        lambda d: expect(d.get("hex_or_text", {}).get("returncode") == 0, "algorithm_aide_read_pref did not reach the device (adb_root_shell wiring)"),
        timeout=60,
    )

    run_case(
        results,
        "hma_read_config",
        "hma_read_config",
        {"timeout": 60},
        lambda d: expect(isinstance(d.get("json"), dict) and "scope" in d.get("json", {}), "HideMyApplist config missing scope"),
        timeout=120,
    )

    run_case(
        results,
        "hma_scope_dry_run",
        "hma_apply_template_to_scope",
        {"target_package": "com.xingin.xhs", "templates": ["LH", "pjgg"], "dry_run": True, "timeout": 60},
        lambda d: expect(d.get("dry_run") is True and "LH" in d.get("after", {}).get("applyTemplates", []), "HMA dry-run did not build scope"),
        timeout=120,
    )

    run_case(
        results,
        "lsposed_modules_query",
        "lsposed_query_config",
        {"sql": "SELECT module_pkg_name, enabled FROM modules ORDER BY module_pkg_name", "max_rows": 20, "timeout": 120},
        lambda d: expect(any(row and row[0] == "com.junge.algorithmAidePro" for row in d.get("rows", [])), "AlgorithmAidePro missing from LSPosed modules"),
        timeout=180,
    )

    run_case(
        results,
        "lsposed_scope_dry_run",
        "lsposed_set_scope",
        {"module_package": "com.junge.algorithmAidePro", "target_package": "com.xingin.xhs", "enabled": True, "dry_run": True, "timeout": 120},
        lambda d: expect(d.get("dry_run") is True and d.get("after", {}).get("scoped") is True, "LSPosed scope dry-run failed"),
        timeout=180,
    )

    local_input_dir = ROOT / "android_mcp" / "_work" / "test_inputs"
    local_input_dir.mkdir(parents=True, exist_ok=True)
    content = f"android-mcp-live-test-{stamp}"
    local_file = local_input_dir / f"live_root_push_{stamp}.txt"
    local_file.write_text(content, encoding="utf-8")
    remote_file = f"/data/local/tmp/android_mcp_live_test_{stamp}.txt"

    run_case(
        results,
        "root_push_file_tmp",
        "root_push_file",
        {"local_path": str(local_file), "remote_path": remote_file, "mode": "644", "timeout": 120},
        lambda d: expect(d.get("install", {}).get("returncode") == 0, "root push install failed"),
        timeout=180,
    )

    run_case(
        results,
        "root_read_file_tmp",
        "root_read_file",
        {"path": remote_file, "max_bytes": 256, "mode": "text", "timeout": 30},
        lambda d: expect(content in str(d.get("result", {}).get("stdout", "")), "root-read did not return pushed content"),
        timeout=120,
    )

    run_case(
        results,
        "root_cleanup_tmp",
        "adb_root_shell",
        {"command": f"rm -f {remote_file}", "timeout": 30},
        lambda d: expect(d.get("returncode") == 0, "cleanup command failed"),
        timeout=120,
    )

    run_case(
        results,
        "reqable_status",
        "reqable_status",
        {},
        lambda d: expect(d.get("info", {}).get("installed") is True, "Reqable is not installed"),
        timeout=120,
    )

    run_case(
        results,
        "topactivity_broadcast_non_ui",
        "intent_broadcast",
        {"action": "com.willme.topactivity.ACTION_NOTIFICATION_RECEIVER", "package": "com.willme.topactivity", "timeout": 30},
        lambda d: expect(d.get("result", {}).get("returncode") == 0, "broadcast command failed"),
        timeout=120,
        required=False,
    )

    run_case(
        results,
        "tcp_probe_optional",
        "tcp_probe_device",
        {"host": "127.0.0.1", "ports": [27042, 27043, 8080, 8888], "timeout": 30},
        lambda d: expect("open_ports" in d, "tcp probe missing open_ports"),
        timeout=120,
        required=False,
    )

    # Regression guard: current_app used `dumpsys window windows`, which dropped the
    # focus lines on Android 12+ and returned an empty focus. The fix uses `dumpsys
    # window` and also surfaces focused_app; a foreground device must report one.
    run_case(
        results,
        "current_app_focus",
        "current_app",
        {},
        lambda d: expect(bool(d.get("focus") or d.get("focused_app")), "current_app returned no focus/focused_app (dumpsys window regression)"),
        timeout=60,
    )

    passed = sum(1 for item in results if item["ok"])
    failed_required = [item for item in results if not item["ok"] and item["required"]]
    report = {
        "schema_version": 1,
        "started_at": stamp,
        "server": str(SERVER),
        "python": PY,
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "failed_required": len(failed_required),
        },
        "results": results,
    }
    report_path = REPORT_DIR / f"frida_orchestrator_live_{stamp}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"[REPORT] {report_path}")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 1 if failed_required else 0


if __name__ == "__main__":
    raise SystemExit(main())

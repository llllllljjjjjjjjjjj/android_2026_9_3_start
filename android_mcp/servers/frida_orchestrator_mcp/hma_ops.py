from __future__ import annotations

import json
import time
from typing import Dict, List, Optional

from android_mcp.common.adb import choose_real_serial

from .adb_ops import _work_path
from .root_ops import root_push_file, root_read_file
from .toolchain import HIDE_MY_APPLIST_PACKAGE


"""Hide My Applist configuration helpers."""

def hma_read_config(serial: Optional[str] = None, timeout: int = 30) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    remote = f"/data/user/0/{HIDE_MY_APPLIST_PACKAGE}/files/config.json"
    read = root_read_file(serial_chosen, remote, max_bytes=2 * 1024 * 1024, mode="text", timeout=timeout)
    parsed = None
    try:
        parsed = json.loads(str(read["result"]["stdout"]))
    except Exception:
        parsed = None
    return {"serial": serial_chosen, "package": HIDE_MY_APPLIST_PACKAGE, "remote": remote, "json": parsed, "read": read}


def hma_write_config(serial: Optional[str], config: Dict[str, object], timeout: int = 60) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    content = json.dumps(config, ensure_ascii=False, separators=(",", ":"))
    local = _work_path("hidemyapplist") / f"config_{int(time.time())}.json"
    local.write_text(content, encoding="utf-8")
    remote = f"/data/user/0/{HIDE_MY_APPLIST_PACKAGE}/files/config.json"
    write = root_push_file(serial_chosen, str(local), remote, mode="600", owner=None, timeout=timeout)
    return {"serial": serial_chosen, "package": HIDE_MY_APPLIST_PACKAGE, "local": str(local), "remote": remote, "write": write, "verify": hma_read_config(serial_chosen, timeout=timeout)}


def hma_apply_template_to_scope(
    serial: Optional[str],
    target_package: str,
    templates: List[str],
    use_whitelist: bool = False,
    exclude_system_apps: bool = True,
    dry_run: bool = True,
    timeout: int = 60,
) -> Dict[str, object]:
    current = hma_read_config(serial, timeout=timeout)
    config = current.get("json") if isinstance(current.get("json"), dict) else {}
    scope = config.setdefault("scope", {})
    before = json.loads(json.dumps(scope.get(target_package, {}), ensure_ascii=False))
    scope[target_package] = {
        "useWhitelist": bool(use_whitelist),
        "excludeSystemApps": bool(exclude_system_apps),
        "applyTemplates": list(templates),
        "extraAppList": list(scope.get(target_package, {}).get("extraAppList", [])) if isinstance(scope.get(target_package), dict) else [],
    }
    if dry_run:
        return {"serial": current["serial"], "target_package": target_package, "dry_run": True, "before": before, "after": scope[target_package], "config_path": current["remote"]}
    write = hma_write_config(current["serial"], config, timeout=timeout)
    return {"serial": current["serial"], "target_package": target_package, "dry_run": False, "before": before, "after": scope[target_package], "write": write}

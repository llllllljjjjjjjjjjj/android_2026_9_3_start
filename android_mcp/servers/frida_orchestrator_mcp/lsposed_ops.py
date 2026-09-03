from __future__ import annotations

import time
import uuid
from typing import Dict, List, Optional

from android_mcp.common.paths import project_root
from android_mcp.common.process import run_command
from android_mcp.common.adb import adb_args, choose_real_serial

from .adb_ops import _optional_local_dir, _q, adb_root_shell
from .root_ops import _pull_sqlite_family, _summarize_sqlite_db, root_push_file, sqlite_query_root


"""LSPosed database and module scope helpers."""

def lsposed_status(serial: Optional[str] = None) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    files = adb_root_shell(serial_chosen, "ls -l /data/adb/lspd/config /data/adb/lspd/log 2>/dev/null | head -120", timeout=20)
    modules = adb_root_shell(serial_chosen, "ls -l /data/adb/modules 2>/dev/null | head -80", timeout=20)
    logs = adb_root_shell(serial_chosen, "log=$(ls -t /data/adb/lspd/log/modules_*.log 2>/dev/null | head -1); if [ -n \"$log\" ]; then tail -n 80 \"$log\"; fi", timeout=30)
    return {"serial": serial_chosen, "files": files, "modules": modules, "log_tail": logs}


def pull_lsposed_db(serial: Optional[str] = None, output_dir: Optional[str] = None) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    base = _optional_local_dir(output_dir, project_root() / "android_mcp" / "_work" / "device_backups" / f"lsposed_{int(time.time())}")
    # Copy ONLY the three canonical files - never `modules_config.db*`. The config
    # dir also holds many `modules_config.db*.bak.<ts>` snapshots written by
    # lsposed_set_scope/set_module_enabled; a glob would drag all of them
    # (dozens of files, hundreds of KB of *-wal.bak) into /data/local/tmp and turn
    # a 2-second pull into a stall. One root round-trip; pull only present files.
    names = ["modules_config.db", "modules_config.db-wal", "modules_config.db-shm"]
    batch = uuid.uuid4().hex
    tmp_map: Dict[str, str] = {n: f"/data/local/tmp/{batch}_{n}" for n in names}
    parts: List[str] = []
    for name in names:
        remote = f"/data/adb/lspd/config/{name}"
        tmp = tmp_map[name]
        parts.append(
            f"if [ -f {_q(remote)} ]; then cp -f {_q(remote)} {_q(tmp)} && chmod 644 {_q(tmp)} && echo PRESENT:{name}; fi"
        )
    copy = adb_root_shell(serial_chosen, "; ".join(parts), timeout=20)
    present_out = str(copy.get("stdout", ""))
    pulled: List[Dict[str, object]] = []
    tmp_to_clean: List[str] = []
    for name in names:
        present = f"PRESENT:{name}" in present_out
        res = None
        if present:
            res = run_command(adb_args(serial_chosen) + ["pull", tmp_map[name], str(base / name)], timeout=60)
            tmp_to_clean.append(tmp_map[name])
        pulled.append({"name": name, "present": present, "pull": res})
    cleanup = None
    if tmp_to_clean:
        cleanup = adb_root_shell(serial_chosen, "rm -f " + " ".join(_q(t) for t in tmp_to_clean), timeout=15)
    return {"serial": serial_chosen, "local_dir": str(base), "copy": copy, "pulls": pulled, "cleanup": cleanup, "summary": _summarize_sqlite_db(base / "modules_config.db")}


def lsposed_query_config(serial: Optional[str], sql: str = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name", max_rows: int = 200, timeout: int = 60) -> Dict[str, object]:
    return sqlite_query_root(serial, "/data/adb/lspd/config/modules_config.db", sql, max_rows=max_rows, timeout=timeout)


def lsposed_list_modules(serial: Optional[str] = None, timeout: int = 60) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    pulled = pull_lsposed_db(serial_chosen)
    summary = pulled.get("summary", {})
    modules = []
    if isinstance(summary, dict):
        for table in summary.get("tables", []):
            name = str(table.get("name", "")).lower()
            if "module" in name or "scope" in name:
                modules.append(table)
    return {"serial": serial_chosen, "db": pulled, "module_like_tables": modules}


def _apply_local_db_to_lsposed(serial_chosen: str, local_db: str, timeout: int) -> Dict[str, object]:
    stamp = int(time.time())
    backup = adb_root_shell(
        serial_chosen,
        (
            "cd /data/adb/lspd/config && "
            f"cp -f modules_config.db modules_config.db.bak.{stamp} 2>/dev/null || true; "
            f"cp -f modules_config.db-wal modules_config.db-wal.bak.{stamp} 2>/dev/null || true; "
            f"cp -f modules_config.db-shm modules_config.db-shm.bak.{stamp} 2>/dev/null || true"
        ),
        timeout=timeout,
    )
    push = root_push_file(serial_chosen, local_db, "/data/adb/lspd/config/modules_config.db", mode="666", timeout=timeout)
    cleanup_wal = adb_root_shell(serial_chosen, "rm -f /data/adb/lspd/config/modules_config.db-wal /data/adb/lspd/config/modules_config.db-shm", timeout=20)
    return {"backup": backup, "push": push, "cleanup_wal": cleanup_wal, "note": "LSPosed may need target app/framework restart before DB changes are consumed."}


def lsposed_set_module_enabled(serial: Optional[str], module_package: str, enabled: bool, dry_run: bool = True, timeout: int = 60) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    pulled = _pull_sqlite_family(serial_chosen, "/data/adb/lspd/config/modules_config.db", timeout)
    import sqlite3

    local_db = str(pulled["local_db"])
    conn = sqlite3.connect(local_db)
    try:
        row = conn.execute("SELECT mid, module_pkg_name, enabled FROM modules WHERE module_pkg_name=?", (module_package,)).fetchone()
        if row is None:
            raise ValueError(f"module not found in LSPosed DB: {module_package}")
        before = {"mid": row[0], "module_pkg_name": row[1], "enabled": bool(row[2])}
        after = before | {"enabled": bool(enabled)}
        if dry_run:
            return {"serial": serial_chosen, "module_package": module_package, "dry_run": True, "before": before, "after": after, "pull": pulled}
        conn.execute("UPDATE modules SET enabled=? WHERE module_pkg_name=?", (1 if enabled else 0, module_package))
        conn.commit()
        try:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass
    finally:
        conn.close()
    apply = _apply_local_db_to_lsposed(serial_chosen, local_db, timeout)
    return {"serial": serial_chosen, "module_package": module_package, "dry_run": False, "before": before, "after": after, "pull": pulled, "apply": apply}


def lsposed_set_scope(
    serial: Optional[str],
    module_package: str,
    target_package: str,
    enabled: bool = True,
    user_id: int = 0,
    dry_run: bool = True,
    timeout: int = 60,
) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    pulled = _pull_sqlite_family(serial_chosen, "/data/adb/lspd/config/modules_config.db", timeout)
    import sqlite3

    local_db = str(pulled["local_db"])
    conn = sqlite3.connect(local_db)
    try:
        module_row = conn.execute("SELECT mid, enabled FROM modules WHERE module_pkg_name=?", (module_package,)).fetchone()
        if module_row is None:
            raise ValueError(f"module not found in LSPosed DB: {module_package}")
        mid = int(module_row[0])
        before_row = conn.execute("SELECT mid, app_pkg_name, user_id FROM scope WHERE mid=? AND app_pkg_name=? AND user_id=?", (mid, target_package, int(user_id))).fetchone()
        before = {"mid": mid, "target_package": target_package, "user_id": int(user_id), "scoped": before_row is not None}
        after = before | {"scoped": bool(enabled)}
        if dry_run:
            return {"serial": serial_chosen, "module_package": module_package, "target_package": target_package, "dry_run": True, "before": before, "after": after, "pull": pulled}
        if enabled:
            conn.execute("INSERT OR IGNORE INTO scope(mid, app_pkg_name, user_id) VALUES (?, ?, ?)", (mid, target_package, int(user_id)))
        else:
            conn.execute("DELETE FROM scope WHERE mid=? AND app_pkg_name=? AND user_id=?", (mid, target_package, int(user_id)))
        conn.commit()
        try:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass
    finally:
        conn.close()
    apply = _apply_local_db_to_lsposed(serial_chosen, local_db, timeout)
    return {"serial": serial_chosen, "module_package": module_package, "target_package": target_package, "dry_run": False, "before": before, "after": after, "pull": pulled, "apply": apply}

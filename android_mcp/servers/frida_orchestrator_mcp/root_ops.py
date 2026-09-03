from __future__ import annotations

import posixpath
import shlex
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from android_mcp.common.paths import project_root
from android_mcp.common.process import run_command
from android_mcp.common.adb import adb_args, choose_real_serial

from .adb_ops import _hash_suffix, _optional_local_dir, _q, _safe_file_name, _work_path, adb_root_shell
from .toolchain import ALGORITHM_AIDE_PACKAGE


"""Root filesystem and SQLite helpers."""

def backup_app_data(serial: Optional[str], package: str = ALGORITHM_AIDE_PACKAGE, output_dir: Optional[str] = None) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    base = _optional_local_dir(output_dir, project_root() / "android_mcp" / "_work" / "device_backups" / f"{package}_{int(time.time())}")
    tar_name = f"{package}_{uuid.uuid4().hex[:8]}.tar.gz"
    remote_tar = f"/data/local/tmp/{tar_name}"
    create = adb_root_shell(serial_chosen, f"tar -czf {remote_tar} -C /data/user/0 {_q(package)}", timeout=120)
    chmod = adb_root_shell(serial_chosen, f"chmod 644 {remote_tar}", timeout=15)
    pull = run_command(adb_args(serial_chosen) + ["pull", remote_tar, str(base / tar_name)], timeout=180)
    cleanup = adb_root_shell(serial_chosen, f"rm -f {remote_tar}", timeout=15)
    return {"serial": serial_chosen, "package": package, "local_tar": str(base / tar_name), "create": create, "chmod": chmod, "pull": pull, "cleanup": cleanup}


def root_ls(serial: Optional[str], path: str, long: bool = True, timeout: int = 20) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    flag = "-la" if long else "-1"
    res = adb_root_shell(serial_chosen, f"ls {flag} {_q(path)}", timeout=timeout)
    return {"serial": serial_chosen, "path": path, "long": long, "result": res}


def root_read_file(serial: Optional[str], path: str, max_bytes: int = 65536, mode: str = "text", timeout: int = 30) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    max_bytes = max(1, min(int(max_bytes), 8 * 1024 * 1024))
    mode_name = (mode or "text").lower()
    quoted = _q(path)
    if mode_name == "hex":
        cmd = f"xxd -l {max_bytes} -g 1 {quoted} 2>/dev/null || toybox xxd -l {max_bytes} -g 1 {quoted} 2>/dev/null || od -An -tx1 -N {max_bytes} {quoted}"
    elif mode_name == "base64":
        cmd = f"head -c {max_bytes} {quoted} | base64"
    else:
        mode_name = "text"
        cmd = f"head -c {max_bytes} {quoted}"
    res = adb_root_shell(serial_chosen, cmd, timeout=timeout)
    return {"serial": serial_chosen, "path": path, "max_bytes": max_bytes, "mode": mode_name, "result": res}


def root_pull_file(
    serial: Optional[str],
    remote_path: str,
    output_dir: Optional[str] = None,
    output_name: Optional[str] = None,
    timeout: int = 120,
) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    local_dir = _optional_local_dir(output_dir, _work_path("root_files") / f"{_safe_file_name(Path(remote_path).name)}_{_hash_suffix(remote_path)}")
    local_name = output_name or Path(remote_path).name or f"pulled_{_hash_suffix(remote_path)}"
    local_path = local_dir / _safe_file_name(local_name)
    tmp = f"/data/local/tmp/{uuid.uuid4().hex}_{_safe_file_name(local_path.name)}"
    copy = adb_root_shell(serial_chosen, f"cp -f {_q(remote_path)} {_q(tmp)} && chmod 644 {_q(tmp)}", timeout=timeout)
    pull = run_command(adb_args(serial_chosen) + ["pull", tmp, str(local_path)], timeout=timeout)
    cleanup = adb_root_shell(serial_chosen, f"rm -f {_q(tmp)}", timeout=15)
    return {"serial": serial_chosen, "remote_path": remote_path, "local_path": str(local_path), "copy": copy, "pull": pull, "cleanup": cleanup}


def root_push_file(
    serial: Optional[str],
    local_path: str,
    remote_path: str,
    mode: str = "644",
    owner: Optional[str] = None,
    timeout: int = 120,
) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    local = Path(local_path)
    if not local.is_absolute():
        local = project_root() / local
    local = local.resolve()
    if not local.exists():
        raise ValueError(f"local file not found: {local}")
    tmp = f"/data/local/tmp/{uuid.uuid4().hex}_{_safe_file_name(local.name)}"
    push = run_command(adb_args(serial_chosen) + ["push", str(local), tmp], timeout=timeout)
    parent = posixpath.dirname(remote_path) or "/"
    parent_q = _q(parent)
    remote_q = _q(remote_path)
    # Discover missing intermediate dirs BEFORE mkdir -p (which runs as root).
    # Then inherit owner from: existing file -> nearest existing ancestor.
    # Newly created dirs get the same owner so an app-private nested first-write
    # does not leave a root:root directory the app cannot enter.
    probe = (
        f"need_dirs=; cur={parent_q}; "
        f"while [ ! -d \"$cur\" ] && [ -n \"$cur\" ] && [ \"$cur\" != / ]; do "
        f"need_dirs=\"$cur $need_dirs\"; cur=$(dirname \"$cur\"); "
        f"done; "
    )
    if owner:
        owner_cmd = probe + f"owner={shlex.quote(owner)};"
    else:
        owner_cmd = probe + (
            f"owner=$(stat -c '%U:%G' {remote_q} 2>/dev/null "
            f"|| stat -c '%u:%g' {remote_q} 2>/dev/null "
            f"|| stat -c '%U:%G' \"$cur\" 2>/dev/null "
            f"|| stat -c '%u:%g' \"$cur\" 2>/dev/null "
            f"|| true);"
        )
    install_cmd = (
        f"{owner_cmd} mkdir -p {parent_q} && cp -f {_q(tmp)} {remote_q} "
        f"&& ( [ -z \"$owner\" ] || chown \"$owner\" {remote_q} || true ) "
        f"&& ( [ -z \"$owner\" ] || [ -z \"$need_dirs\" ] || chown \"$owner\" $need_dirs || true ) "
        f"&& chmod {shlex.quote(mode)} {remote_q}"
    )
    install = adb_root_shell(serial_chosen, install_cmd, timeout=timeout)
    cleanup = adb_root_shell(serial_chosen, f"rm -f {_q(tmp)}", timeout=15)
    return {"serial": serial_chosen, "local_path": str(local), "remote_path": remote_path, "mode": mode, "owner": owner, "push": push, "install": install, "cleanup": cleanup}


def _pull_sqlite_family(serial_chosen: str, db_path: str, timeout: int) -> Dict[str, object]:
    """Pull a SQLite DB and its sidecars efficiently, matching the bare-adb path.

    One root round-trip copies every family member that actually exists into
    /data/local/tmp (no glob -> never drags unrelated ``*.bak.*`` snapshots), then
    we ``adb pull`` only the present members and clean them up in a single ``rm``.
    Per-op timeouts are bounded and additionally clamped by the caller's tool
    deadline, so this can never accumulate the multi-minute budget that used to
    wedge the server when adbd was momentarily slow.
    """
    base_dir = _work_path("sqlite") / f"{_safe_file_name(Path(db_path).name)}_{_hash_suffix(db_path)}_{int(time.time())}"
    base_dir.mkdir(parents=True, exist_ok=True)
    local_db = base_dir / (Path(db_path).name or "database.db")
    suffixes = ["", "-wal", "-shm", "-journal"]
    batch = uuid.uuid4().hex
    tmp_map: Dict[str, str] = {}
    parts: List[str] = []
    for suffix in suffixes:
        remote = f"{db_path}{suffix}"
        tmp = f"/data/local/tmp/{batch}_{_safe_file_name(local_db.name)}{suffix}"
        tmp_map[suffix] = tmp
        label = suffix or "db"
        parts.append(
            f"if [ -f {_q(remote)} ]; then cp -f {_q(remote)} {_q(tmp)} && chmod 644 {_q(tmp)} && echo PRESENT:{label}; fi"
        )
    probe = adb_root_shell(serial_chosen, "; ".join(parts), timeout=max(10, min(int(timeout), 30)))
    present_out = str(probe.get("stdout", ""))

    pulls: List[Dict[str, object]] = []
    tmp_to_clean: List[str] = []
    for suffix in suffixes:
        remote = f"{db_path}{suffix}"
        local = base_dir / f"{local_db.name}{suffix}"
        present = f"PRESENT:{suffix or 'db'}" in present_out
        pull = None
        if present:
            pull = run_command(adb_args(serial_chosen) + ["pull", tmp_map[suffix], str(local)], timeout=max(10, min(int(timeout), 60)))
            tmp_to_clean.append(tmp_map[suffix])
        pulls.append({"remote": remote, "local": str(local), "present": present, "copy": probe, "pull": pull})
    cleanup = None
    if tmp_to_clean:
        cleanup = adb_root_shell(serial_chosen, "rm -f " + " ".join(_q(t) for t in tmp_to_clean), timeout=15)
    return {"local_dir": str(base_dir), "local_db": str(local_db), "pulls": pulls, "cleanup": cleanup, "probe": probe}


def sqlite_query_root(serial: Optional[str], db_path: str, sql: str, max_rows: int = 200, timeout: int = 60) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    query = (sql or "").strip()
    lowered = query.lower()
    if lowered == ".schema":
        query = "SELECT type, name, tbl_name, sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type, name"
    elif not (lowered.startswith("select") or lowered.startswith("pragma") or lowered.startswith("with")):
        raise ValueError("sqlite_query_root is read-only; use SELECT, PRAGMA, WITH or .schema")
    pulled = _pull_sqlite_family(serial_chosen, db_path, timeout)
    import sqlite3

    rows: List[List[object]] = []
    columns: List[str] = []
    truncated = False
    local_db = pulled["local_db"]
    # The device DB may not exist yet (e.g. the app hasn't created it). Opening a
    # missing/empty file with mode=ro raises "unable to open database file" which
    # bubbles up as an opaque -32603. Return an explicit, non-error result instead
    # so callers can branch on db_exists.
    if not Path(local_db).exists() or Path(local_db).stat().st_size == 0:
        return {
            "serial": serial_chosen,
            "db_path": db_path,
            "sql": query,
            "local_dir": pulled["local_dir"],
            "columns": [],
            "rows": [],
            "row_count": 0,
            "truncated": False,
            "db_exists": False,
            "note": f"database not present on device (or empty): {db_path}",
            "pull": pulled,
        }
    conn = sqlite3.connect(f"{Path(local_db).as_uri()}?mode=ro", uri=True)
    try:
        cur = conn.execute(query)
        columns = [desc[0] for desc in (cur.description or [])]
        fetched = cur.fetchmany(max_rows + 1)
        if len(fetched) > max_rows:
            truncated = True
            fetched = fetched[:max_rows]
        rows = [list(row) for row in fetched]
    finally:
        conn.close()
    return {
        "serial": serial_chosen,
        "db_path": db_path,
        "sql": query,
        "local_dir": pulled["local_dir"],
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "truncated": truncated,
        "pull": pulled,
    }


def _summarize_sqlite_db(path: Path) -> Dict[str, object]:
    if not path.exists() or path.stat().st_size == 0:
        return {"exists": path.exists(), "tables": []}
    try:
        import sqlite3

        conn = sqlite3.connect(str(path))
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        tables = []
        for (name,) in rows:
            cols = conn.execute(f"PRAGMA table_info({name})").fetchall()
            count = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            sample = conn.execute(f"SELECT * FROM {name} LIMIT 5").fetchall()
            tables.append({"name": name, "columns": [c[1] for c in cols], "count": count, "sample": [list(r) for r in sample]})
        conn.close()
        return {"exists": True, "tables": tables}
    except Exception as exc:
        return {"exists": True, "error": str(exc)}

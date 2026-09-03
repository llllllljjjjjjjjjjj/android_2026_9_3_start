from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from android_mcp.common.paths import default_decompiled_path, target_artifacts


SOURCE_EXTS = {".java", ".kt", ".smali", ".xml", ".json", ".properties", ".txt"}
SYMBOL_PATTERNS = [
    re.compile(r"\b(?:class|interface|enum|object)\s+([A-Za-z_$][\w$]*)"),
    re.compile(r"\b(?:public|private|protected|static|final|native|synchronized|\s)+\s*[\w<>\[\].?,\s]+\s+([A-Za-z_$][\w$]*)\s*\("),
    re.compile(r"^\.method\b.*?\s+([A-Za-z_$<>][\w$<>]*)\(", re.M),
]
ENDPOINT_PATTERNS = [
    re.compile(r"https?://[^\s\"'<>\\)]+", re.I),
    re.compile(r"@(?:GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s*\(\s*\"([^\"]+)\"", re.I),
    re.compile(r"\.url\s*\(\s*\"([^\"]+)\"", re.I),
]
STRING_PATTERN = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"')
SUSPICIOUS_PATTERN = re.compile(
    r"(sign|signature|x-sign|x_sign|shield|token|nonce|timestamp|encrypt|decrypt|cipher|hmac|sha|md5|mac|digest|base64|gzip|crc)",
    re.I,
)


def db_path_for_target(target: str) -> Path:
    return target_artifacts(target) / "reverse_index.sqlite"


def connect_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY,
            path TEXT UNIQUE NOT NULL,
            ext TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            size INTEGER NOT NULL,
            mtime REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS lines (
            file_id INTEGER NOT NULL,
            line_no INTEGER NOT NULL,
            text TEXT NOT NULL,
            PRIMARY KEY(file_id, line_no)
        );
        CREATE TABLE IF NOT EXISTS symbols (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            kind TEXT NOT NULL,
            file_id INTEGER NOT NULL,
            line_no INTEGER NOT NULL,
            context TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
        CREATE TABLE IF NOT EXISTS strings (
            id INTEGER PRIMARY KEY,
            value TEXT NOT NULL,
            file_id INTEGER NOT NULL,
            line_no INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_strings_value ON strings(value);
        CREATE TABLE IF NOT EXISTS endpoints (
            id INTEGER PRIMARY KEY,
            value TEXT NOT NULL,
            file_id INTEGER NOT NULL,
            line_no INTEGER NOT NULL,
            source TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_endpoints_value ON endpoints(value);
        """
    )
    conn.commit()


def iter_source_files(root: Path, max_file_mb: int) -> Iterable[Path]:
    max_bytes = max_file_mb * 1024 * 1024
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in {".git", "build", ".gradle", "__pycache__"}]
        for name in files:
            path = Path(current) / name
            if path.suffix.lower() not in SOURCE_EXTS:
                continue
            try:
                if path.stat().st_size <= max_bytes:
                    yield path
            except OSError:
                continue


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def index_project(target: str, decompiled_path: Optional[str] = None, force: bool = False, max_file_mb: int = 5) -> Dict[str, object]:
    source_root = Path(decompiled_path).resolve() if decompiled_path else default_decompiled_path(target).resolve()
    if not source_root.exists():
        raise ValueError(f"decompiled path not found: {source_root}")
    db_path = db_path_for_target(target)
    conn = connect_db(db_path)
    init_db(conn)
    if force:
        conn.executescript("DELETE FROM lines; DELETE FROM symbols; DELETE FROM strings; DELETE FROM endpoints; DELETE FROM files;")
        conn.commit()

    started = time.time()
    files_seen = 0
    lines_seen = 0
    symbols_seen = 0
    endpoints_seen = 0
    strings_seen = 0

    for path in iter_source_files(source_root, max_file_mb=max_file_mb):
        rel = str(path.relative_to(source_root)).replace("\\", "/")
        stat = path.stat()
        sha = file_sha256(path)
        existing = conn.execute("SELECT id, sha256 FROM files WHERE path = ?", (rel,)).fetchone()
        if existing and existing["sha256"] == sha and not force:
            continue
        if existing:
            file_id = int(existing["id"])
            conn.execute("DELETE FROM lines WHERE file_id = ?", (file_id,))
            conn.execute("DELETE FROM symbols WHERE file_id = ?", (file_id,))
            conn.execute("DELETE FROM strings WHERE file_id = ?", (file_id,))
            conn.execute("DELETE FROM endpoints WHERE file_id = ?", (file_id,))
            conn.execute(
                "UPDATE files SET ext=?, sha256=?, size=?, mtime=? WHERE id=?",
                (path.suffix.lower(), sha, stat.st_size, stat.st_mtime, file_id),
            )
        else:
            cur = conn.execute(
                "INSERT INTO files(path, ext, sha256, size, mtime) VALUES(?,?,?,?,?)",
                (rel, path.suffix.lower(), sha, stat.st_size, stat.st_mtime),
            )
            file_id = int(cur.lastrowid)

        text = read_text(path)
        for line_no, line in enumerate(text.splitlines(), 1):
            conn.execute("INSERT OR REPLACE INTO lines(file_id, line_no, text) VALUES(?,?,?)", (file_id, line_no, line))
            lines_seen += 1
            for match in STRING_PATTERN.finditer(line):
                value = match.group(1)
                if value:
                    conn.execute("INSERT INTO strings(value, file_id, line_no) VALUES(?,?,?)", (value, file_id, line_no))
                    strings_seen += 1
            for pattern in ENDPOINT_PATTERNS:
                for match in pattern.finditer(line):
                    value = match.group(1) if match.lastindex else match.group(0)
                    conn.execute("INSERT INTO endpoints(value, file_id, line_no, source) VALUES(?,?,?,?)", (value, file_id, line_no, pattern.pattern[:40]))
                    endpoints_seen += 1
        for pattern in SYMBOL_PATTERNS:
            for match in pattern.finditer(text):
                prefix = text[: match.start()]
                line_no = prefix.count("\n") + 1
                context = text.splitlines()[line_no - 1][:500] if text.splitlines() and line_no <= len(text.splitlines()) else ""
                conn.execute(
                    "INSERT INTO symbols(name, kind, file_id, line_no, context) VALUES(?,?,?,?,?)",
                    (match.group(1), "symbol", file_id, line_no, context),
                )
                symbols_seen += 1
        files_seen += 1

    conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('source_root', ?)", (str(source_root),))
    conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('indexed_at', ?)", (time.strftime("%Y-%m-%dT%H:%M:%S"),))
    conn.commit()
    conn.close()
    return {
        "target": target,
        "source_root": str(source_root),
        "db_path": str(db_path),
        "files_indexed_or_updated": files_seen,
        "lines_indexed": lines_seen,
        "symbols_added": symbols_seen,
        "strings_added": strings_seen,
        "endpoints_added": endpoints_seen,
        "elapsed_seconds": round(time.time() - started, 3),
    }


def source_root_from_db(conn: sqlite3.Connection, target: str) -> Path:
    row = conn.execute("SELECT value FROM meta WHERE key='source_root'").fetchone()
    if row:
        return Path(row["value"])
    return default_decompiled_path(target).resolve()


def require_db(target: str) -> tuple[sqlite3.Connection, Path]:
    path = db_path_for_target(target)
    if not path.exists():
        raise ValueError(f"index db not found for target {target}; call index_project first")
    conn = connect_db(path)
    return conn, source_root_from_db(conn, target)


def rows_to_results(rows: Iterable[sqlite3.Row], source_root: Path) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for row in rows:
        rel = row["path"]
        item = {key: row[key] for key in row.keys()}
        item["absolute_path"] = str((source_root / rel).resolve())
        out.append(item)
    return out


def search_code(target: str, query: str, regex: bool = False, limit: int = 50) -> Dict[str, object]:
    conn, source_root = require_db(target)
    if regex:
        pattern = re.compile(query)
        rows = conn.execute(
            "SELECT f.path, l.line_no, l.text FROM lines l JOIN files f ON f.id=l.file_id"
        ).fetchall()
        matched = [r for r in rows if pattern.search(r["text"])][:limit]
    else:
        matched = conn.execute(
            "SELECT f.path, l.line_no, l.text FROM lines l JOIN files f ON f.id=l.file_id WHERE l.text LIKE ? LIMIT ?",
            (f"%{query}%", limit),
        ).fetchall()
    conn.close()
    return {"target": target, "query": query, "results": rows_to_results(matched, source_root)}


def search_table(target: str, table: str, value_col: str, query: str, limit: int = 50) -> Dict[str, object]:
    conn, source_root = require_db(target)
    sql = f"SELECT f.path, t.line_no, t.{value_col} AS value FROM {table} t JOIN files f ON f.id=t.file_id WHERE t.{value_col} LIKE ? LIMIT ?"
    rows = conn.execute(sql, (f"%{query}%", limit)).fetchall()
    conn.close()
    return {"target": target, "query": query, "results": rows_to_results(rows, source_root)}


def find_symbol(target: str, name: str, limit: int = 50) -> Dict[str, object]:
    conn, source_root = require_db(target)
    rows = conn.execute(
        "SELECT f.path, s.line_no, s.name, s.kind, s.context FROM symbols s JOIN files f ON f.id=s.file_id WHERE s.name LIKE ? LIMIT ?",
        (f"%{name}%", limit),
    ).fetchall()
    conn.close()
    return {"target": target, "name": name, "results": rows_to_results(rows, source_root)}


def list_suspicious_sign_methods(target: str, limit: int = 80) -> Dict[str, object]:
    conn, source_root = require_db(target)
    rows = conn.execute(
        "SELECT f.path, s.line_no, s.name, s.context FROM symbols s JOIN files f ON f.id=s.file_id"
    ).fetchall()
    matched = [r for r in rows if SUSPICIOUS_PATTERN.search(r["name"]) or SUSPICIOUS_PATTERN.search(r["context"])][:limit]
    conn.close()
    return {"target": target, "results": rows_to_results(matched, source_root)}


def open_source(target: str, file: str, line: int = 1, context: int = 8) -> Dict[str, object]:
    conn, source_root = require_db(target)
    rel = file.replace("\\", "/")
    row = conn.execute("SELECT id, path FROM files WHERE path = ? OR path LIKE ? LIMIT 1", (rel, f"%{rel}")).fetchone()
    if not row:
        conn.close()
        raise ValueError(f"file not found in index: {file}")
    start = max(1, line - context)
    end = line + context
    rows = conn.execute(
        "SELECT line_no, text FROM lines WHERE file_id=? AND line_no BETWEEN ? AND ? ORDER BY line_no",
        (row["id"], start, end),
    ).fetchall()
    conn.close()
    return {
        "target": target,
        "file": row["path"],
        "absolute_path": str((source_root / row["path"]).resolve()),
        "line": line,
        "context": [{"line_no": r["line_no"], "text": r["text"]} for r in rows],
    }


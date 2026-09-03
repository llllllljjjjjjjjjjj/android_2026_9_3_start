from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional


# --- Cooperative per-call deadline -------------------------------------------
# A single MCP tool handler frequently issues *many* sequential subprocess calls
# (e.g. pulling a SQLite family = 4x cp + pull + rm). Each call carries its own
# ``timeout``, so the handler's aggregate budget can be several multiples of the
# server's tool-level wall timeout (``ANDROID_MCP_TOOL_TIMEOUT``). When that
# happens the worker thread stays blocked inside ``communicate()`` long after the
# tool has already reported a timeout to the client - and because the stdio
# server is single-worker and serialized, that one wedged call bricks the whole
# MCP until the handler finishes on its own (observed: 90s "timeout" followed by
# every subsequent tool returning "MCP tool busy").
#
# The dispatcher installs a monotonic deadline (thread-local, scoped to one tool
# call) before invoking a handler. ``run_command`` caps every subprocess timeout
# to the remaining budget and refuses to even spawn a child once the deadline has
# passed. The handler therefore unwinds within one poll of the deadline instead
# of running to natural completion, which lets the server release its lock on the
# normal path. Threads cannot be force-killed in Python; making the *subprocess*
# (which can be killed) the timeout authority is what makes the wall timeout real.
_CALL_DEADLINE = threading.local()


def set_call_deadline(seconds_from_now: Optional[float]) -> None:
    """Bind a deadline ``seconds_from_now`` monotonic seconds ahead to this thread.

    Passing ``None`` clears it. Scoped per-thread so the single executor worker
    can carry a fresh deadline per tool call without leaking into the next one.
    """
    if seconds_from_now is None:
        _CALL_DEADLINE.value = None
    else:
        _CALL_DEADLINE.value = time.monotonic() + max(0.0, float(seconds_from_now))


def clear_call_deadline() -> None:
    _CALL_DEADLINE.value = None


def call_deadline_remaining() -> Optional[float]:
    """Seconds left on this thread's deadline, or ``None`` when unset."""
    deadline = getattr(_CALL_DEADLINE, "value", None)
    if deadline is None:
        return None
    return deadline - time.monotonic()


# Floor for the deadline clamp. Essential short ops - above all the ``adb
# devices`` enumeration that every tool runs via choose_real_serial() - must be
# allowed to finish even when the tool deadline is nearly spent. Without a floor,
# a nearly-exhausted deadline could chop ``adb devices`` down to ~1s and a slow
# cold enumeration would be killed, failing the whole tool with a spurious
# "device not found / timed out". The floor never RAISES a caller's own shorter
# timeout (see run_command) - it only stops the deadline from cutting below it.
_MIN_SUBPROCESS_TIMEOUT_S = max(1.0, float(os.environ.get("ANDROID_MCP_MIN_SUBPROCESS_TIMEOUT", "5")))


def _child_env(env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Build the environment for a spawned child.

    Always a COPY of ``os.environ`` (so PATH and friends are preserved on
    Windows) with the caller's overrides applied, plus adb's mDNS discovery
    forced off. adb's mDNS network scan makes every ``adb devices`` take 4-5s
    even with a single wired USB device (measured), which dominates device
    selection latency and, combined with the tool deadline, can starve the
    enumeration; disabling it drops ``adb devices`` to ~0.1s. These vars only
    take effect when the adb *server* starts, and any client command may be the
    one that auto-launches it, so we inject them into every child (adb reads
    them; every other tool ignores them). Override with ANDROID_MCP_ADB_MDNS=1.
    """
    child: Dict[str, str] = dict(os.environ)
    if env:
        child.update(env)
    mdns = os.environ.get("ANDROID_MCP_ADB_MDNS", "0")
    child["ADB_MDNS"] = mdns
    child["ADB_MDNS_OPENSCREEN"] = mdns
    return child


def which_or_env(env_name: str, default_name: str) -> str:
    env_value = os.environ.get(env_name)
    if env_value:
        return env_value
    found = shutil.which(default_name)
    if found:
        return found
    return default_name


def _decode_output(raw: object) -> str:
    # adb/frida emit UTF-8, but native Windows tools (taskkill/cmd) emit the OEM
    # code page (cp936 on zh-CN Windows). Decoding everything as UTF-8 turned
    # taskkill output into mojibake. Try UTF-8 first, then the local OEM page.
    if not raw:
        return ""
    if isinstance(raw, str):
        return raw
    for enc in ("utf-8", "cp936", "gbk", "mbcs"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def _kill_process_tree(pid: int) -> None:
    """Best-effort kill of pid and children. Critical on Windows where
    TerminateProcess does not cascade to adb/frida child trees."""
    if pid <= 0:
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                shell=False,
            )
        else:
            os.kill(pid, 9)
    except Exception:
        pass


def run_command(
    args: List[str],
    timeout: int = 30,
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    input_text: Optional[str] = None,
) -> Dict[str, object]:
    """Run a subprocess with a hard wall-clock timeout.

    Unlike bare ``subprocess.run(..., timeout=...)``, timeouts are converted into
    a structured result (``timed_out=True``) and the process *tree* is killed on
    Windows so a wedged ``adb.exe`` client cannot leave the MCP server blocked.

    The effective timeout is additionally clamped to the caller's tool-level
    deadline (see ``set_call_deadline``). This guarantees that a handler which
    fires a long chain of subprocess calls can never keep the single server
    worker (and its lock) busy past ``ANDROID_MCP_TOOL_TIMEOUT``: once the
    deadline is blown we return immediately without spawning, so the handler
    unwinds and the lock is freed.
    """
    remaining = call_deadline_remaining()
    if remaining is not None:
        if remaining <= 0:
            # Deadline already blown by earlier subprocess calls in this handler.
            # Do not spawn another child; unwind now so the worker thread returns
            # and the server lock is released instead of wedging every next call.
            return {
                "args": args,
                "returncode": -9,
                "stdout": "",
                "stderr": "[skipped: tool deadline exceeded before spawn]",
                "timed_out": True,
                "deadline_skipped": True,
            }
        # Never let one child outlive the tool's remaining wall-clock budget, but
        # never chop an essential op below the floor either. This never RAISES a
        # caller's own shorter timeout: when the deadline is not binding
        # (timeout <= remaining) the caller's timeout is used as-is.
        timeout = min(float(timeout), max(float(remaining), _MIN_SUBPROCESS_TIMEOUT_S))

    creationflags = 0
    if os.name == "nt":
        # CREATE_NEW_PROCESS_GROUP helps taskkill /T tear down the tree.
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

    proc = subprocess.Popen(
        args,
        cwd=str(cwd) if cwd else None,
        env=_child_env(env),
        stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        creationflags=creationflags,
    )
    try:
        stdout_b, stderr_b = proc.communicate(
            input=input_text.encode("utf-8") if input_text is not None else None,
            timeout=timeout,
        )
        return {
            "args": args,
            "returncode": proc.returncode,
            "stdout": _decode_output(stdout_b),
            "stderr": _decode_output(stderr_b),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        _kill_process_tree(proc.pid)
        try:
            stdout_b, stderr_b = proc.communicate(timeout=2)
        except Exception:
            stdout_b, stderr_b = b"", b""
            try:
                proc.kill()
            except Exception:
                pass
        stderr_text = _decode_output(stderr_b)
        marker = f"[timeout after {timeout}s]"
        if marker not in stderr_text:
            stderr_text = (stderr_text + "\n" + marker).strip()
        return {
            "args": args,
            "returncode": -9,
            "stdout": _decode_output(stdout_b),
            "stderr": stderr_text,
            "timed_out": True,
        }


def start_background(
    args: List[str],
    stdout_path: Path,
    stderr_path: Path,
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
) -> subprocess.Popen[str]:
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_handle = stdout_path.open("a", encoding="utf-8", errors="replace")
    stderr_handle = stderr_path.open("a", encoding="utf-8", errors="replace")
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS  # type: ignore[attr-defined]
    proc = subprocess.Popen(
        args,
        cwd=str(cwd) if cwd else None,
        env=_child_env(env),
        stdout=stdout_handle,
        stderr=stderr_handle,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        creationflags=creationflags,
    )
    # The child inherited its own handles; close the parent copies so the server
    # process does not leak two file handles per background session.
    stdout_handle.close()
    stderr_handle.close()
    return proc


def tail_text(path: Path, lines: int = 200) -> str:
    if not path.exists():
        return ""
    # Simple robust tail for moderate hook logs.
    content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(content[-lines:])

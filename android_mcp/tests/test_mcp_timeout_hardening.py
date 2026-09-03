"""Device-independent regression tests for MCP timeout / lock hardening.

These prove the systemic fixes for `frida-orchestrator-mcp` wedging WITHOUT any
real device, adb, or MCP instance. They exercise the two layers directly:

  1. common.process.run_command      -> cooperative deadline clamps + kills the
                                        child subprocess (no residual process).
  2. common.mcp_stdio.StdioMcpServer -> the serial lock is ALWAYS released on
                                        timeout, and a wedged worker is abandoned
                                        so the next call is never "MCP tool busy".
  3. common.process._child_env       -> ADB_MDNS/ADB_MDNS_OPENSCREEN=0 reach every
                                        spawned child (kills the 4s mDNS scan) with
                                        PATH/etc preserved, and the deadline clamp
                                        floor keeps essential ops (adb devices) from
                                        being chopped below ~5s.

A `python -c "... time.sleep(N) ..."` child stands in for a wedged
`adb shell su -c` call. Run with the venv python:

    .venv-frida-16.5.9\\Scripts\\python.exe android_mcp\\tests\\test_mcp_timeout_hardening.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from android_mcp.common import process  # noqa: E402
from android_mcp.common.mcp_stdio import StdioMcpServer, object_schema  # noqa: E402

PY = sys.executable
# Child: touch <start>, sleep <secs>, touch <finish>. If we kill it mid-sleep the
# finish sentinel never appears -> proof the process really died.
CHILD = (
    "import sys,time;"
    "open(sys.argv[1],'w').close();"
    "time.sleep(int(sys.argv[2]));"
    "open(sys.argv[3],'w').close()"
)

_failures = []


def check(cond: bool, msg: str) -> None:
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {msg}")
    if not cond:
        _failures.append(msg)


def _sleeper_args(tmp: Path, tag: str, secs: int):
    start = tmp / f"{tag}.start"
    finish = tmp / f"{tag}.finish"
    return [PY, "-c", CHILD, str(start), str(secs), str(finish)], start, finish


# --------------------------------------------------------------------------- #
# Test 1: run_command honours the cooperative deadline and kills the child.
# --------------------------------------------------------------------------- #
def test_deadline_kills_subprocess(tmp: Path) -> None:
    print("test_deadline_kills_subprocess")
    args, start, finish = _sleeper_args(tmp, "t1", 8)
    process.set_call_deadline(2)  # 2s budget, child wants 8s
    t0 = time.monotonic()
    try:
        res = process.run_command(args, timeout=60)  # asks 60s; deadline wins
    finally:
        process.clear_call_deadline()
    elapsed = time.monotonic() - t0

    check(elapsed < 6, f"returned in {elapsed:.1f}s (deadline 2s cut the 60s ask)")
    check(bool(res.get("timed_out")), "result marked timed_out=True")
    check(start.exists(), "child actually started (start sentinel present)")
    # Wait past the child's own sleep; finish must NEVER appear -> it was killed.
    deadline = time.monotonic() + 9
    while time.monotonic() < deadline:
        if finish.exists():
            break
        time.sleep(0.2)
    check(not finish.exists(), "child was killed before completing (no finish sentinel / no residual process)")


# --------------------------------------------------------------------------- #
# Test 2: a handler that fires MANY subprocess calls cannot exceed the budget.
#         (models _pull_sqlite_family: cp+pull+rm x family members)
# --------------------------------------------------------------------------- #
def test_multi_subprocess_budget_clamp(tmp: Path) -> None:
    print("test_multi_subprocess_budget_clamp")
    calls = []
    process.set_call_deadline(3)
    t0 = time.monotonic()
    try:
        for i in range(6):
            args, _, _ = _sleeper_args(tmp, f"t2_{i}", 5)  # each wants 5s
            calls.append(process.run_command(args, timeout=5))
    finally:
        process.clear_call_deadline()
    elapsed = time.monotonic() - t0

    check(elapsed < 8, f"6x 5s ops collapsed to {elapsed:.1f}s (was up to 30s+)")
    skipped = [c for c in calls if c.get("deadline_skipped")]
    check(len(skipped) >= 3, f"later ops skipped once budget blown ({len(skipped)}/6 deadline_skipped)")


# --------------------------------------------------------------------------- #
# Test 3: cooperative timeout -> lock released, next call is NOT busy, executor
#         reused (worker unwound on its own via the deadline).
# --------------------------------------------------------------------------- #
def test_lock_released_after_subprocess_timeout(tmp: Path) -> None:
    print("test_lock_released_after_subprocess_timeout")
    srv = StdioMcpServer("test-coop")
    srv._tool_timeout = 6
    srv._deadline_margin = 3   # subprocess deadline = 3s
    srv._wedge_grace = 2

    @srv.tool("slow_sub", "sleep in a child", object_schema({}))
    def slow_sub():  # noqa: ANN202
        args, _, _ = _sleeper_args(tmp, "t3", 20)
        return {"sub": process.run_command(args, timeout=20)}

    @srv.tool("fast", "instant", object_schema({}))
    def fast():  # noqa: ANN202
        return {"ok": True, "value": 42}

    executor_before = srv._executor
    t0 = time.monotonic()
    slow_res = srv._call_tool_guarded({"name": "slow_sub", "arguments": {}})
    elapsed = time.monotonic() - t0
    check(elapsed < 6, f"cooperative slow call returned in {elapsed:.1f}s without hitting wall timeout")
    # Worker unwound by itself, so the executor must NOT have been abandoned.
    check(srv._executor is executor_before, "executor reused (cooperative unwind, no thread leak)")

    # The critical assertion: the very next call must succeed, not raise busy.
    t0 = time.monotonic()
    fast_res = srv._call_tool_guarded({"name": "fast", "arguments": {}})
    fast_elapsed = time.monotonic() - t0
    check(fast_elapsed < 2, f"next call ran immediately ({fast_elapsed:.2f}s) - lock was released")
    text = fast_res["content"][0]["text"]
    check('"value": 42' in text, "next call returned correct result (not a busy error)")


# --------------------------------------------------------------------------- #
# Test 4: NON-cooperative wedge (pure-Python sleep ignoring the deadline) still
#         does not brick the server: worker abandoned, lock released, next OK.
# --------------------------------------------------------------------------- #
def test_lock_released_after_pure_python_wedge() -> None:
    print("test_lock_released_after_pure_python_wedge")
    srv = StdioMcpServer("test-wedge")
    srv._tool_timeout = 4
    srv._deadline_margin = 2
    srv._wedge_grace = 1

    @srv.tool("wedge", "ignores deadline", object_schema({}))
    def wedge():  # noqa: ANN202
        time.sleep(30)  # pure Python: un-killable, ignores the subprocess deadline
        return {"never": True}

    @srv.tool("fast", "instant", object_schema({}))
    def fast():  # noqa: ANN202
        return {"ok": True, "value": 7}

    executor_before = srv._executor
    raised = False
    t0 = time.monotonic()
    try:
        srv._call_tool_guarded({"name": "wedge", "arguments": {}})
    except TimeoutError as exc:
        raised = True
        check("abandoned" in str(exc), "wedge raised a clear abandon/timeout error")
    elapsed = time.monotonic() - t0
    check(raised, "wedge call raised TimeoutError (did not hang forever)")
    check(elapsed < 9, f"wedge gave up in {elapsed:.1f}s (~tool_timeout+grace)")
    check(srv._executor is not executor_before, "wedged executor was abandoned and replaced")

    # Even though a wedged worker thread is still sleeping in the background, the
    # next call must land on the fresh worker immediately.
    t0 = time.monotonic()
    fast_res = srv._call_tool_guarded({"name": "fast", "arguments": {}})
    fast_elapsed = time.monotonic() - t0
    check(fast_elapsed < 2, f"next call ran immediately ({fast_elapsed:.2f}s) despite the still-sleeping wedged thread")
    check('"value": 7' in fast_res["content"][0]["text"], "next call returned correct result")


# --------------------------------------------------------------------------- #
# Test 5: fast path unaffected - no deadline set means normal completion.
# --------------------------------------------------------------------------- #
def test_fast_path_unaffected(tmp: Path) -> None:
    print("test_fast_path_unaffected")
    process.clear_call_deadline()
    args, start, finish = _sleeper_args(tmp, "t5", 0)  # sleep 0 -> completes
    t0 = time.monotonic()
    res = process.run_command(args, timeout=30)
    elapsed = time.monotonic() - t0
    check(not res.get("timed_out"), "quick command not marked timed_out")
    check(res.get("returncode") == 0, "quick command returned rc=0")
    check(finish.exists(), "quick command ran to completion (finish sentinel present)")
    check(elapsed < 10, f"quick command was quick ({elapsed:.1f}s)")


# --------------------------------------------------------------------------- #
# Test 6: ADB_MDNS/ADB_MDNS_OPENSCREEN=0 are injected into every child env, and
#         the parent env (PATH, ...) is preserved (not cleared).
# --------------------------------------------------------------------------- #
def test_adb_mdns_env_injected() -> None:
    print("test_adb_mdns_env_injected")
    process.clear_call_deadline()
    probe = (
        "import os;"
        "print('ADB_MDNS=' + str(os.environ.get('ADB_MDNS')));"
        "print('ADB_MDNS_OPENSCREEN=' + str(os.environ.get('ADB_MDNS_OPENSCREEN')));"
        "print('PATH_LEN=' + str(len(os.environ.get('PATH', ''))))"
    )
    res = process.run_command([PY, "-c", probe], timeout=30)
    out = str(res.get("stdout", ""))
    check("ADB_MDNS=0" in out, "ADB_MDNS=0 injected into child env")
    check("ADB_MDNS_OPENSCREEN=0" in out, "ADB_MDNS_OPENSCREEN=0 injected into child env")
    # PATH must survive (Windows: env is a COPY of os.environ, not a bare dict).
    path_len = 0
    for line in out.splitlines():
        if line.startswith("PATH_LEN="):
            path_len = int(line.split("=", 1)[1] or "0")
    check(path_len > 0, f"parent env preserved (child PATH len={path_len}, not cleared)")

    # Also assert directly on the assembled env dict.
    child_env = process._child_env(None)
    check(child_env.get("ADB_MDNS") == "0", "_child_env(None) sets ADB_MDNS=0")
    check(child_env.get("ADB_MDNS_OPENSCREEN") == "0", "_child_env(None) sets ADB_MDNS_OPENSCREEN=0")
    check(bool(child_env.get("PATH") or child_env.get("Path")), "_child_env keeps PATH from os.environ")
    merged = process._child_env({"CUSTOM_KEY": "keep"})
    check(merged.get("CUSTOM_KEY") == "keep", "_child_env merges caller-supplied env keys")


# --------------------------------------------------------------------------- #
# Test 7: the deadline clamp floor lets an essential op (stand-in: 3s child)
#         finish even when the deadline is almost spent - it is NOT chopped to 1s.
#         (This is the adb-devices-vs-mDNS collision, fixed as double insurance.)
# --------------------------------------------------------------------------- #
def test_floor_protects_essential_op(tmp: Path) -> None:
    print("test_floor_protects_essential_op")
    floor = process._MIN_SUBPROCESS_TIMEOUT_S
    check(floor >= 5, f"deadline clamp floor is ~5s (is {floor}s)")
    args, start, finish = _sleeper_args(tmp, "t7", 3)  # essential op needs 3s
    process.set_call_deadline(0.3)  # deadline almost gone
    t0 = time.monotonic()
    try:
        res = process.run_command(args, timeout=10)
    finally:
        process.clear_call_deadline()
    elapsed = time.monotonic() - t0
    check(not res.get("timed_out"), "essential op survived a near-spent deadline (floor kept it >=3s, not 1s)")
    check(finish.exists(), "essential op ran to completion")
    check(elapsed < 6, f"and still returned promptly ({elapsed:.1f}s)")


# --------------------------------------------------------------------------- #
# Test 8: the floor never RAISES a caller's own shorter timeout.
# --------------------------------------------------------------------------- #
def test_floor_does_not_raise_explicit_short_timeout(tmp: Path) -> None:
    print("test_floor_does_not_raise_explicit_short_timeout")
    args, _, finish = _sleeper_args(tmp, "t8", 10)  # child wants 10s
    process.set_call_deadline(100)  # deadline NOT binding
    t0 = time.monotonic()
    try:
        res = process.run_command(args, timeout=2)  # caller explicitly wants <=2s
    finally:
        process.clear_call_deadline()
    elapsed = time.monotonic() - t0
    check(bool(res.get("timed_out")), "explicit 2s timeout still fired (floor did not inflate it to 5s)")
    check(elapsed < 4.5, f"killed at ~2s ({elapsed:.1f}s), not raised to the 5s floor")
    check(not finish.exists(), "child killed (explicit short timeout honored)")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="mcp_timeout_test_") as d:
        tmp = Path(d)
        test_deadline_kills_subprocess(tmp)
        test_multi_subprocess_budget_clamp(tmp)
        test_lock_released_after_subprocess_timeout(tmp)
        test_lock_released_after_pure_python_wedge()
        test_fast_path_unaffected(tmp)
        test_adb_mdns_env_injected()
        test_floor_protects_essential_op(tmp)
        test_floor_does_not_raise_explicit_short_timeout(tmp)

    print()
    if _failures:
        print(f"RESULT: {len(_failures)} FAILED")
        for f in _failures:
            print(f"  - {f}")
        return 1
    print("RESULT: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

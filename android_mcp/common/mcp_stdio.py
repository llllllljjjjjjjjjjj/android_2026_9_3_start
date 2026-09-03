from __future__ import annotations

import json
import os
import sys
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Optional

try:
    from .process import clear_call_deadline, set_call_deadline
except ImportError:  # pragma: no cover - tolerate mid-edit / partial sync of process.py
    def set_call_deadline(seconds_from_now=None):  # type: ignore[misc]
        return None

    def clear_call_deadline():  # type: ignore[misc]
        return None


JsonDict = Dict[str, Any]
ToolHandler = Callable[..., Any]

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


@dataclass
class McpTool:
    name: str
    description: str
    input_schema: JsonDict
    handler: ToolHandler

    def to_protocol(self) -> JsonDict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


class StdioMcpServer:
    """Small dependency-free MCP stdio server.

    It implements the JSON-RPC methods used by common MCP clients:
    initialize, tools/list, tools/call, resources/list, prompts/list and ping.
    The transport is newline-delimited JSON over stdin/stdout.

    Tool handlers run one-at-a-time (stdio is inherently serial). A hard wall
    timeout (``ANDROID_MCP_TOOL_TIMEOUT``, default 90s) ensures a wedged adb/frida
    call returns an error to the client instead of sitting until the client's
    ~300s abort. Parallel CallMcpTool from the client still queues; prefer
    sequential health checks over fan-out.

    Timeout handling has two cooperating layers so a single slow call can never
    brick the server:

    * The worker installs a per-call subprocess *deadline* (tool timeout minus a
      small margin). ``common.process.run_command`` honours it, so subprocess
      handlers unwind on their own just before the wall timeout and the lock is
      released on the normal path.
    * If a handler ignores the deadline (pure-Python spin, un-killable native
      call), the wall timeout still fires; we then abandon that worker's executor
      and hand the next call a fresh worker. The lock is ALWAYS released in
      ``finally`` - never held waiting for a wedged future to finish.
    """

    def __init__(self, name: str, version: str = "0.1.0") -> None:
        self.name = name
        self.version = version
        self._tools: Dict[str, McpTool] = {}
        self._tool_lock = threading.Lock()
        self._executor_lock = threading.Lock()
        self._executor = self._new_executor()
        self._tool_timeout = max(5, int(os.environ.get("ANDROID_MCP_TOOL_TIMEOUT", "90")))
        # Subprocesses must stop a little BEFORE the wall timeout so the worker
        # can unwind and return a structured result while the client still waits.
        self._deadline_margin = max(1, int(os.environ.get("ANDROID_MCP_TOOL_DEADLINE_MARGIN", "8")))
        if self._deadline_margin >= self._tool_timeout:
            self._deadline_margin = max(1, self._tool_timeout // 3)
        # Extra time we let a wedged (deadline-ignoring) worker unwind before we
        # abandon its executor thread and rebuild a fresh one.
        self._wedge_grace = max(1, int(os.environ.get("ANDROID_MCP_TOOL_WEDGE_GRACE", "5")))

    def _new_executor(self) -> ThreadPoolExecutor:
        return ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"{self.name}-tool")

    def tool(self, name: str, description: str, input_schema: JsonDict) -> Callable[[ToolHandler], ToolHandler]:
        def decorator(func: ToolHandler) -> ToolHandler:
            self._tools[name] = McpTool(name, description, input_schema, func)
            return func

        return decorator

    def run(self) -> None:
        for raw_line in sys.stdin:
            line = raw_line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = self._dispatch(request)
                if response is not None:
                    self._write(response)
            except Exception as exc:  # pragma: no cover - defensive server boundary
                self._write(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32603,
                            "message": f"internal error: {exc}",
                            "data": traceback.format_exc(limit=8),
                        },
                    }
                )

    def _dispatch(self, request: JsonDict) -> Optional[JsonDict]:
        method = request.get("method")
        request_id = request.get("id")
        params = request.get("params") or {}

        # Notifications have no id. MCP clients commonly send notifications/initialized.
        if request_id is None and method and method.startswith("notifications/"):
            return None

        try:
            if method == "initialize":
                result = {
                    "protocolVersion": params.get("protocolVersion", "2025-06-18"),
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": self.name, "version": self.version},
                }
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": [tool.to_protocol() for tool in self._tools.values()]}
            elif method == "tools/call":
                result = self._call_tool_guarded(params)
            elif method == "resources/list":
                result = {"resources": []}
            elif method == "prompts/list":
                result = {"prompts": []}
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"method not found: {method}"},
                }
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except ValueError as exc:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": str(exc)}}
        except Exception as exc:  # pragma: no cover - defensive server boundary
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"tool error: {exc}",
                    "data": traceback.format_exc(limit=8),
                },
            }

    def _call_tool_guarded(self, params: JsonDict) -> JsonDict:
        """Serialize tool calls and enforce a wall-clock timeout.

        Clients often fan out multiple CallMcpTool in one turn. This server can
        only process them sequentially over stdio; without a hard timeout a single
        stuck adb/frida handler makes the whole batch appear hung until the
        client's ~300s abort.
        """
        name = params.get("name") or "?"
        # Fail fast if a previous timed-out worker is still holding the lock. With
        # the fixes below this should be rare (the lock is always released in
        # finally), but keep the guard so genuine concurrent fan-out still queues.
        if not self._tool_lock.acquire(timeout=2):
            raise TimeoutError(
                f"MCP tool busy (previous call still running). "
                f"Avoid parallel CallMcpTool; retry shortly. waiting_for={name}"
            )
        try:
            with self._executor_lock:
                executor = self._executor
            deadline = max(1, self._tool_timeout - self._deadline_margin)
            future = executor.submit(self._call_tool, params, deadline)
            try:
                return future.result(timeout=self._tool_timeout)
            except FuturesTimeout as exc:
                # The worker installs the same deadline for its subprocess calls,
                # so a well-behaved handler is already unwinding. Give it a brief
                # grace to return on its own (cooperative path, executor reused).
                if self._await_future(future, self._wedge_grace):
                    return future.result(timeout=0)
                # Still stuck -> it is ignoring the deadline (pure-Python spin or
                # an un-killable native call). Abandon this executor's thread and
                # rebuild a fresh worker so the NEXT call is not queued behind the
                # wedged one. The lock is released by `finally` regardless.
                self._abandon_executor(executor)
                raise TimeoutError(
                    f"tool '{name}' exceeded ANDROID_MCP_TOOL_TIMEOUT={self._tool_timeout}s "
                    f"and its worker was abandoned. The MCP stays responsive - retry. "
                    f"If this recurs, split the call or raise ANDROID_MCP_TOOL_TIMEOUT."
                ) from exc
        finally:
            # Always release. A single timed-out call must never keep the lock and
            # wedge every subsequent tool.
            self._tool_lock.release()

    @staticmethod
    def _await_future(future: Any, grace: float) -> bool:
        """Return True if the future finished within ``grace`` seconds (any way)."""
        try:
            future.result(timeout=grace)
            return True
        except FuturesTimeout:
            return False
        except Exception:
            # Completed by raising -> still "done"; caller re-reads the result.
            return True

    def _abandon_executor(self, wedged: ThreadPoolExecutor) -> None:
        """Replace a wedged single-worker executor with a fresh one.

        The wedged worker thread cannot be killed, but its in-flight subprocess
        is deadline-capped and will return shortly, after which the thread exits.
        We do not wait for it; the important thing is that the next tool call gets
        an idle worker instead of queueing behind the stuck one.
        """
        with self._executor_lock:
            if self._executor is wedged:
                self._executor = self._new_executor()
        try:
            wedged.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            # Python < 3.9 has no cancel_futures kwarg.
            try:
                wedged.shutdown(wait=False)
            except Exception:
                pass
        except Exception:
            pass

    def _call_tool(self, params: JsonDict, deadline_seconds: Optional[float] = None) -> JsonDict:
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name not in self._tools:
            raise ValueError(f"unknown tool: {name}")
        tool = self._tools[name]
        # Tolerate arguments the schema does not declare. Some MCP clients attach
        # extra fields (e.g. a `description`) to every tools/call; forwarding them
        # straight into the handler raises TypeError -> opaque -32603, which was the
        # single biggest source of spurious "tool failed" errors. Drop unknown keys
        # so one stray field never breaks an otherwise valid call.
        allowed = set((tool.input_schema.get("properties") or {}).keys())
        call_args = {k: v for k, v in arguments.items() if k in allowed} if allowed else dict(arguments)
        # Install the subprocess deadline for the duration of this call so nested
        # run_command() invocations self-cap. Always clear it (the executor reuses
        # one worker thread; a stale deadline must not bleed into the next call).
        if deadline_seconds is not None:
            set_call_deadline(deadline_seconds)
        try:
            data = tool.handler(**call_args)
        finally:
            if deadline_seconds is not None:
                clear_call_deadline()
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(data, ensure_ascii=False, indent=2, default=str),
                }
            ],
            "isError": False,
        }

    def _write(self, message: JsonDict) -> None:
        sys.stdout.write(json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n")
        sys.stdout.flush()


def object_schema(properties: JsonDict, required: Optional[Iterable[str]] = None) -> JsonDict:
    schema: JsonDict = {"type": "object", "properties": properties, "additionalProperties": False}
    if required:
        schema["required"] = list(required)
    return schema


def string_prop(description: str, default: Optional[str] = None) -> JsonDict:
    prop: JsonDict = {"type": "string", "description": description}
    if default is not None:
        prop["default"] = default
    return prop


def int_prop(description: str, default: Optional[int] = None, minimum: Optional[int] = None, maximum: Optional[int] = None) -> JsonDict:
    prop: JsonDict = {"type": "integer", "description": description}
    if default is not None:
        prop["default"] = default
    if minimum is not None:
        prop["minimum"] = minimum
    if maximum is not None:
        prop["maximum"] = maximum
    return prop


def bool_prop(description: str, default: Optional[bool] = None) -> JsonDict:
    prop: JsonDict = {"type": "boolean", "description": description}
    if default is not None:
        prop["default"] = default
    return prop


def array_prop(description: str, items: JsonDict) -> JsonDict:
    return {"type": "array", "description": description, "items": items}

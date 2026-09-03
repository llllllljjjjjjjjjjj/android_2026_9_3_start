from __future__ import annotations

import json
import os
import re
import shlex
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from android_mcp.common.paths import project_root, safe_output_path, target_artifacts, target_hooks
from android_mcp.common.process import run_command, start_background, tail_text
from android_mcp.common.adb import adb_args, choose_real_serial

from .adb_ops import _q, _work_path, adb_root_shell
from .toolchain import PATCHED_FRIDA_SERVER, REMOTE_PATCHED_FRIDA, _mcp_env


"""Frida server, hook session and RPC helpers."""

def session_db_path(target: str) -> Path:
    return target_artifacts(target) / "frida_sessions.json"


def load_sessions(target: str) -> Dict[str, Dict[str, object]]:
    path = session_db_path(target)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def save_sessions(target: str, sessions: Dict[str, Dict[str, object]]) -> None:
    path = session_db_path(target)
    path.write_text(json.dumps(sessions, ensure_ascii=False, indent=2), encoding="utf-8")


def frida_devices(timeout: int = 10) -> Dict[str, object]:
    bridge = _work_path("frida_cli") / f"devices_{uuid.uuid4().hex}.py"
    bridge.write_text(
        """
import json, os
import frida

rows = []
for dev in frida.enumerate_devices():
    rows.append({"id": dev.id, "name": dev.name, "type": dev.type})
print(json.dumps({"devices": rows}, ensure_ascii=False))
""".strip(),
        encoding="utf-8",
    )
    try:
        return run_command([sys.executable, str(bridge)], timeout=timeout, cwd=project_root(), env=_mcp_env())
    finally:
        try:
            bridge.unlink()
        except OSError:
            pass


def frida_ps(serial: Optional[str] = None, timeout: int = 20) -> Dict[str, object]:
    # Use -U by default after validating that ADB sees a real phone.
    serial_chosen = choose_real_serial(serial)
    bridge = _work_path("frida_cli") / f"ps_{uuid.uuid4().hex}.py"
    bridge.write_text(
        """
import json
import os
import frida

def pick(obj, names):
    return {name: getattr(obj, name, None) for name in names}

explicit = os.environ.get("ANDROID_MCP_FRIDA_DEVICE", "").strip()
device = frida.get_device(explicit, timeout=10) if explicit else frida.get_usb_device(timeout=10)
apps = [pick(app, ["identifier", "name", "pid", "parameters"]) for app in device.enumerate_applications()]
processes = [pick(proc, ["pid", "name", "parameters"]) for proc in device.enumerate_processes()]
frontmost = None
try:
    frontmost = pick(device.get_frontmost_application(), ["identifier", "name", "pid", "parameters"])
except Exception:
    frontmost = None
print(json.dumps({"device": {"id": device.id, "name": device.name, "type": device.type}, "frontmost": frontmost, "applications": apps, "processes": processes}, ensure_ascii=False, default=str))
""".strip(),
        encoding="utf-8",
    )
    try:
        result = run_command(
            [sys.executable, str(bridge)],
            timeout=timeout,
            cwd=project_root(),
            env=_mcp_env({"ANDROID_MCP_FRIDA_DEVICE": serial_chosen}),
        )
        result["adb_serial_checked"] = serial_chosen
        return result
    finally:
        try:
            bridge.unlink()
        except OSError:
            pass


def _validate_frida_listen(listen: str) -> str:
    value = (listen or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.:\[\]-]{3,128}", value):
        raise ValueError(f"invalid frida listen endpoint: {listen!r}")
    return value


def push_patched_frida_server(serial: Optional[str] = None, local_path: Optional[str] = None, remote_path: str = REMOTE_PATCHED_FRIDA) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    local = Path(local_path) if local_path else PATCHED_FRIDA_SERVER
    if not local.exists():
        raise ValueError(f"patched frida-server not found: {local}")
    remote_q = _q(remote_path)
    push = run_command(adb_args(serial_chosen) + ["push", str(local), remote_path], timeout=180)
    chmod = adb_root_shell(serial_chosen, f"chmod 755 {remote_q}", timeout=20)
    # Magisk/frida builds may treat `--version` as "start server"; wrap with
    # toybox timeout so status never blocks the MCP stdio loop.
    sha = adb_root_shell(
        serial_chosen,
        f"sha256sum {remote_q}; (timeout 3s {remote_q} --version || timeout 3 {remote_q} --version || true) 2>&1 | head -5",
        timeout=20,
    )
    return {"serial": serial_chosen, "local": str(local), "remote": remote_path, "push": push, "chmod": chmod, "remote_check": sha}


def patched_frida_status(serial: Optional[str] = None, remote_path: str = REMOTE_PATCHED_FRIDA) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    remote_q = _q(remote_path)
    # Never run new-server bare: some builds ignore --version and stay resident,
    # which wedged adb shell (and the single-threaded MCP) until Cursor's ~300s abort.
    cmd = (
        f"if [ -f {remote_q} ]; then ls -l {remote_q}; sha256sum {remote_q}; "
        f"(timeout 3s {remote_q} --version || timeout 3 {remote_q} --version || echo VERSION_SKIPPED) 2>&1 | head -5; "
        f"else echo MISSING; fi; "
        "ps -A | grep -E 'frida|new-server|fs_run' || true"
    )
    res = adb_root_shell(serial_chosen, cmd, timeout=15)
    return {"serial": serial_chosen, "remote": remote_path, "status": res}


def start_patched_frida_server(
    serial: Optional[str] = None,
    remote_path: str = REMOTE_PATCHED_FRIDA,
    listen: str = "0.0.0.0:27042",
    kill_existing: bool = True,
) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    checks = []
    if kill_existing:
        checks.append(adb_root_shell(serial_chosen, "pkill -f frida-server || true; pkill -f new-server || true; pkill -f fs_run || true", timeout=15))
    remote_q = _q(remote_path)
    listen_q = shlex.quote(_validate_frida_listen(listen))
    cmd = f"chmod 755 {remote_q}; nohup {remote_q} -l {listen_q} >/data/local/tmp/new-server.log 2>&1 &"
    start = adb_root_shell(serial_chosen, cmd, timeout=20)
    time.sleep(1.0)
    status = patched_frida_status(serial_chosen, remote_path)
    return {"serial": serial_chosen, "remote": remote_path, "listen": listen, "pre": checks, "start": start, "status": status}


def stop_patched_frida_server(serial: Optional[str] = None) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    res = adb_root_shell(serial_chosen, "pkill -f frida-server || true; pkill -f new-server || true; pkill -f fs_run || true", timeout=15)
    return {"serial": serial_chosen, "result": res, "status": patched_frida_status(serial_chosen)}


def frida_rpc_call(package: str, script_path: str, method: str, args: Optional[List[object]] = None, serial: Optional[str] = None, spawn: bool = False, timeout: int = 30, pid: Optional[int] = None) -> Dict[str, object]:
    """One-shot Frida RPC call.

    The JS script must define rpc.exports = { methodName(...) { ... } }.
    This intentionally runs as a short-lived process so MCP callers can use it
    like an algorithm oracle without managing a long session.
    """
    serial_chosen = choose_real_serial(serial)
    script = Path(script_path)
    if not script.is_absolute():
        script = project_root() / script
    if not script.exists():
        raise ValueError(f"script not found: {script}")

    bridge_dir = project_root() / "android_mcp" / "_work" / "frida_rpc"
    bridge_dir.mkdir(parents=True, exist_ok=True)
    bridge = bridge_dir / f"rpc_bridge_{uuid.uuid4().hex}.py"
    payload = {
        "package": package,
        "script": str(script),
        "method": method,
        "args": args or [],
        "spawn": spawn,
        "pid": pid,
        "explicit_device": os.environ.get("ANDROID_MCP_FRIDA_DEVICE", "").strip() or serial_chosen,
    }
    bridge.write_text(
        """
import json, sys, time
import frida

payload = json.loads(sys.stdin.read())
events = []

def on_message(message, data):
    events.append({"message": message, "data_hex": data.hex() if data else None})

explicit = payload.get("explicit_device")
device = frida.get_device(explicit, timeout=10) if explicit else frida.get_usb_device(timeout=10)
pid = None
explicit_pid = payload.get("pid")
if payload.get("spawn"):
    pid = device.spawn([payload["package"]])
    session = device.attach(pid)
elif explicit_pid:
    session = device.attach(int(explicit_pid))
else:
    try:
        session = device.attach(payload["package"])
    except frida.ProcessNotFoundError:
        raise RuntimeError("frida found no process named '%s'. Run frida_ps for the exact process name/pid, then retry with pid=<pid> or spawn=true." % payload["package"])
script = session.create_script(open(payload["script"], "r", encoding="utf-8").read())
script.on("message", on_message)
script.load()
if pid is not None:
    device.resume(pid)
time.sleep(0.2)
exports = script.exports_sync
method = getattr(exports, payload["method"])
result = method(*payload.get("args", []))
print(json.dumps({"ok": True, "result": result, "events": events}, ensure_ascii=False, default=str))
session.detach()
""".strip(),
        encoding="utf-8",
    )
    try:
        proc = run_command(
            [sys.executable, str(bridge)],
            timeout=timeout,
            cwd=project_root(),
            env=_mcp_env({"PYTHONIOENCODING": "utf-8"}),
            input_text=json.dumps(payload, ensure_ascii=False),
        )
        return {"serial": serial_chosen, "package": package, "script": str(script), "method": method, "args": args or [], "result": proc}
    finally:
        try:
            bridge.unlink()
        except OSError:
            pass


def generate_frida_rpc_template(target: str, output: Optional[str] = None, class_name: Optional[str] = None, method_name: Optional[str] = None) -> Dict[str, object]:
    hook_dir = target_hooks(target)
    class_line = json.dumps(class_name or "com.example.SignUtil")
    method_line = json.dumps(method_name or "sign")
    content = f"""// Generated by frida-orchestrator-mcp.
// Edit CLASS_NAME and METHOD_NAME, then call through frida_rpc_call.
var CLASS_NAME = {class_line};
var METHOD_NAME = {method_line};

function asStringArray(xs) {{
  var out = [];
  for (var i = 0; i < xs.length; i++) out.push(String(xs[i]));
  return out;
}}

rpc.exports = {{
  ping: function () {{
    return "pong";
  }},
  callstatic: function () {{
    var args = arguments;
    var result = null;
    Java.perform(function () {{
      var T = Java.use(CLASS_NAME);
      result = String(T[METHOD_NAME].apply(T, args));
    }});
    return result;
  }},
  callinstancefirst: function () {{
    var args = arguments;
    var result = null;
    Java.perform(function () {{
      Java.choose(CLASS_NAME, {{
        onMatch: function (obj) {{
          if (result == null) result = String(obj[METHOD_NAME].apply(obj, args));
        }},
        onComplete: function () {{}}
      }});
    }});
    return result;
  }}
}};
"""
    out = safe_output_path(hook_dir, output, "rpc_algorithm_oracle.js")
    out.write_text(content, encoding="utf-8")
    return {"target": target, "path": str(out), "class_name": class_name, "method_name": method_name}


def template_java_method(class_name: str, method_name: str) -> str:
    return f"""// Generated by frida-orchestrator-mcp
Java.perform(function () {{
  const Target = Java.use({json.dumps(class_name)});
  Target[{json.dumps(method_name)}].overloads.forEach(function (overload, idx) {{
    overload.implementation = function () {{
      const args = Array.prototype.slice.call(arguments).map(function (v) {{ return String(v); }});
      console.log(JSON.stringify({{type: "java_method_enter", className: {json.dumps(class_name)}, methodName: {json.dumps(method_name)}, overload: idx, args: args}}));
      const ret = overload.call(this, ...arguments);
      console.log(JSON.stringify({{type: "java_method_leave", className: {json.dumps(class_name)}, methodName: {json.dumps(method_name)}, overload: idx, ret: String(ret)}}));
      return ret;
    }};
  }});
}});
"""


def template_crypto() -> str:
    return r"""// Generated by frida-orchestrator-mcp
Java.perform(function () {
  function bytesToHex(bytes) {
    if (!bytes) return null;
    const out = [];
    for (let i = 0; i < bytes.length; i++) out.push(('0' + (bytes[i] & 0xff).toString(16)).slice(-2));
    return out.join('');
  }
  const MessageDigest = Java.use('java.security.MessageDigest');
  const mdGetInstance = MessageDigest.getInstance.overload('java.lang.String');
  mdGetInstance.implementation = function (alg) {
    console.log(JSON.stringify({type: 'crypto_get_digest', algorithm: String(alg)}));
    return mdGetInstance.call(MessageDigest, alg);
  };
  const mdDigestBytes = MessageDigest.digest.overload('[B');
  mdDigestBytes.implementation = function (input) {
    const ret = mdDigestBytes.call(this, input);
    console.log(JSON.stringify({type: 'crypto_digest', inputHex: bytesToHex(input), outputHex: bytesToHex(ret)}));
    return ret;
  };
  const Mac = Java.use('javax.crypto.Mac');
  const macGetInstance = Mac.getInstance.overload('java.lang.String');
  macGetInstance.implementation = function (alg) {
    console.log(JSON.stringify({type: 'crypto_get_mac', algorithm: String(alg)}));
    return macGetInstance.call(Mac, alg);
  };
  const macDoFinalBytes = Mac.doFinal.overload('[B');
  macDoFinalBytes.implementation = function (input) {
    const ret = macDoFinalBytes.call(this, input);
    console.log(JSON.stringify({type: 'crypto_mac', inputHex: bytesToHex(input), outputHex: bytesToHex(ret)}));
    return ret;
  };
  const Cipher = Java.use('javax.crypto.Cipher');
  const cipherGetInstance = Cipher.getInstance.overload('java.lang.String');
  cipherGetInstance.implementation = function (transformation) {
    console.log(JSON.stringify({type: 'crypto_get_cipher', transformation: String(transformation)}));
    return cipherGetInstance.call(Cipher, transformation);
  };
});
"""


def template_okhttp() -> str:
    return r"""// Generated by frida-orchestrator-mcp
Java.perform(function () {
  try {
    const RealCall = Java.use('okhttp3.RealCall');
    const execute0 = RealCall.execute.overload();
    execute0.implementation = function () {
      const req = this.request();
      console.log(JSON.stringify({type: 'okhttp_execute', method: String(req.method()), url: String(req.url()), headers: String(req.headers())}));
      return execute0.call(this);
    };
  } catch (e) {
    console.log(JSON.stringify({type: 'template_error', template: 'okhttp', error: String(e)}));
  }
});
"""


def template_system_loadlibrary() -> str:
    return r"""// Generated by frida-orchestrator-mcp
Java.perform(function () {
  const System = Java.use('java.lang.System');
  const loadLibrary0 = System.loadLibrary.overload('java.lang.String');
  loadLibrary0.implementation = function (name) {
    console.log(JSON.stringify({type: 'loadLibrary', name: String(name)}));
    return loadLibrary0.call(System, name);
  };
});
"""


def template_register_natives() -> str:
    return r"""// Generated by frida-orchestrator-mcp
const symbols = Module.enumerateSymbolsSync('libart.so');
const target = symbols.find(s => s.name.indexOf('RegisterNatives') >= 0 && s.name.indexOf('CheckJNI') < 0);
if (target) {
  Interceptor.attach(target.address, {
    onEnter(args) {
      console.log(JSON.stringify({type: 'RegisterNatives', address: String(target.address)}));
    }
  });
}
"""


def generate_hook_template(
    target: str,
    template: str,
    class_name: Optional[str] = None,
    method_name: Optional[str] = None,
    output: Optional[str] = None,
) -> Dict[str, object]:
    hook_dir = target_hooks(target)
    template_name = template.lower().strip()
    if template_name == "java_method":
        if not class_name or not method_name:
            raise ValueError("java_method template requires class_name and method_name")
        content = template_java_method(class_name, method_name)
        default = f"hook_{class_name.split('.')[-1]}_{method_name}.js"
    elif template_name == "crypto":
        content = template_crypto()
        default = "hook_crypto.js"
    elif template_name == "okhttp":
        content = template_okhttp()
        default = "hook_okhttp.js"
    elif template_name == "system_loadlibrary":
        content = template_system_loadlibrary()
        default = "hook_system_loadlibrary.js"
    elif template_name == "register_natives":
        content = template_register_natives()
        default = "hook_register_natives.js"
    else:
        raise ValueError("unknown template; use java_method, crypto, okhttp, system_loadlibrary, register_natives")
    out_path = safe_output_path(hook_dir, output, default)
    out_path.write_text(content, encoding="utf-8")
    return {"target": target, "template": template_name, "path": str(out_path), "bytes": len(content.encode("utf-8"))}


def start_frida_hook(target: str, package: str, script_path: str, serial: Optional[str] = None, spawn: bool = True, pid: Optional[int] = None) -> Dict[str, object]:
    serial_chosen = choose_real_serial(serial)
    script = Path(script_path)
    if not script.is_absolute():
        script = target_hooks(target) / script
    script = script.resolve()
    if not script.exists():
        raise ValueError(f"hook script not found: {script}")
    artifacts = target_artifacts(target)
    session_id = f"{package.replace('.', '_')}_{int(time.time())}"
    stdout_path = artifacts / f"{session_id}.frida.out.log"
    stderr_path = artifacts / f"{session_id}.frida.err.log"
    payload_path = artifacts / f"{session_id}.frida.payload.json"
    runner_path = artifacts / f"{session_id}.frida_runner.py"
    payload_path.write_text(
        json.dumps(
            {
                "package": package,
                "script": str(script),
                "spawn": bool(spawn),
                "pid": pid,
                "explicit_device": os.environ.get("ANDROID_MCP_FRIDA_DEVICE", "").strip() or serial_chosen,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    runner_path.write_text(
        """
import json, sys, time, traceback
import frida

payload = json.loads(open(sys.argv[1], "r", encoding="utf-8").read())

def emit(obj):
    print(json.dumps(obj, ensure_ascii=False, default=str), flush=True)

def on_message(message, data):
    emit({"event": "message", "message": message, "data_hex": data.hex() if data else None})

try:
    explicit = payload.get("explicit_device")
    device = frida.get_device(explicit, timeout=10) if explicit else frida.get_usb_device(timeout=10)
    spawned_pid = None
    explicit_pid = payload.get("pid")
    if payload.get("spawn"):
        spawned_pid = device.spawn([payload["package"]])
        session = device.attach(spawned_pid)
    elif explicit_pid:
        session = device.attach(int(explicit_pid))
    else:
        try:
            session = device.attach(payload["package"])
        except frida.ProcessNotFoundError:
            raise RuntimeError("frida found no process named '%s'. Run frida_ps for the exact process name/pid, then retry with pid=<pid> or spawn=true." % payload["package"])
    source = open(payload["script"], "r", encoding="utf-8").read()
    script = session.create_script(source)
    script.on("message", on_message)
    script.load()
    if spawned_pid is not None:
        device.resume(spawned_pid)
    emit({"event": "ready", "device": {"id": device.id, "name": device.name, "type": device.type}, "package": payload["package"], "pid": spawned_pid if spawned_pid is not None else explicit_pid})
    while True:
        time.sleep(1)
except Exception as exc:
    emit({"event": "error", "error": repr(exc), "traceback": traceback.format_exc(limit=8)})
    raise
""".strip(),
        encoding="utf-8",
    )
    args = [sys.executable, str(runner_path), str(payload_path)]
    proc = start_background(args, stdout_path, stderr_path, env=_mcp_env())
    sessions = load_sessions(target)
    sessions[session_id] = {
        "pid": proc.pid,
        "package": package,
        "script": str(script),
        "adb_serial_checked": serial_chosen,
        "args": args,
        "runner": str(runner_path),
        "payload": str(payload_path),
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    save_sessions(target, sessions)
    return sessions[session_id] | {"session_id": session_id}


def list_frida_sessions(target: str) -> Dict[str, object]:
    return {"target": target, "sessions": load_sessions(target)}


def read_frida_log(target: str, session_id: str, lines: int = 200) -> Dict[str, object]:
    sessions = load_sessions(target)
    if session_id not in sessions:
        raise ValueError(f"unknown session_id: {session_id}")
    session = sessions[session_id]
    return {
        "session_id": session_id,
        "stdout_tail": tail_text(Path(str(session["stdout"])), lines),
        "stderr_tail": tail_text(Path(str(session["stderr"])), lines),
    }


def stop_frida_session(target: str, session_id: str) -> Dict[str, object]:
    sessions = load_sessions(target)
    if session_id not in sessions:
        raise ValueError(f"unknown session_id: {session_id}")
    pid = int(sessions[session_id]["pid"])
    result = run_command(["taskkill", "/PID", str(pid), "/T", "/F"], timeout=10)
    sessions[session_id]["stopped_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    sessions[session_id]["stop_result"] = result
    save_sessions(target, sessions)
    return {"session_id": session_id, "pid": pid, "taskkill": result}

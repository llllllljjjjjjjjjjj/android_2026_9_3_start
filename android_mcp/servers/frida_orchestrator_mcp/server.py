from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from android_mcp.common.mcp_stdio import StdioMcpServer, array_prop, bool_prop, int_prop, object_schema, string_prop
from android_mcp.servers.frida_orchestrator_mcp import hooks


server = StdioMcpServer("frida-orchestrator-mcp", "0.1.0")

STRING_MAP = {"type": "object", "description": "String key/value map.", "additionalProperties": {"type": "string"}}
JSON_OBJECT = {"type": "object", "description": "JSON object."}


@server.tool(
    "adb_devices",
    "List Android devices; defaults to real-device filtering.",
    object_schema({"real_only": bool_prop("Filter emulator-like devices.", True)}),
)
def adb_devices(real_only: bool = True):
    return hooks.adb_devices(real_only)


@server.tool(
    "adb_shell",
    "Run an adb shell command on a real device.",
    object_schema(
        {
            "command": string_prop("Shell command to run on device."),
            "serial": string_prop("Optional adb serial. Must be real-device unless ANDROID_MCP_ALLOW_EMULATOR=1."),
            "timeout": int_prop("Timeout seconds.", 20, 1, 300),
        },
        required=["command"],
    ),
)
def adb_shell(command: str, serial: str | None = None, timeout: int = 20):
    return hooks.adb_shell(serial, command, timeout)


@server.tool(
    "adb_root_shell",
    "Run an adb shell command through su -c on a real rooted device.",
    object_schema(
        {
            "command": string_prop("Root shell command."),
            "serial": string_prop("Optional adb serial."),
            "timeout": int_prop("Timeout seconds.", 20, 1, 300),
        },
        required=["command"],
    ),
)
def adb_root_shell(command: str, serial: str | None = None, timeout: int = 20):
    return hooks.adb_root_shell(serial, command, timeout)


@server.tool("device_health", "Summarize real-device, root and patched frida-server health.", object_schema({"serial": string_prop("Optional adb serial.")}))
def device_health(serial: str | None = None):
    return hooks.device_health(serial)


@server.tool("toolchain_status", "Report the portable android_mcp toolchain, bundled ADB/APKs/frida-server and selected device.", object_schema({"serial": string_prop("Optional adb serial.")}))
def toolchain_status(serial: str | None = None):
    return hooks.toolchain_status(serial)


@server.tool(
    "adb_connect",
    "Connect ADB to a TCP endpoint, then list devices. Useful after changing phones/computers.",
    object_schema({"endpoint": string_prop("ADB TCP endpoint, e.g. 192.168.1.10:5555."), "timeout": int_prop("Timeout seconds.", 30, 1, 120)}, required=["endpoint"]),
)
def adb_connect(endpoint: str, timeout: int = 30):
    return hooks.adb_connect(endpoint, timeout)


@server.tool(
    "install_bundled_reverse_apks",
    "Install cached reverse-tool APKs from android_mcp/toolchain/apks/device-tools onto the real device.",
    object_schema(
        {
            "serial": string_prop("Optional adb serial."),
            "packages": array_prop("Optional package names to install. Omit to install all cached tool APKs.", {"type": "string"}),
            "reinstall": bool_prop("Use adb install -r.", True),
            "grant": bool_prop("Use adb install -g.", True),
            "timeout": int_prop("Timeout seconds.", 300, 1, 1800),
        },
    ),
)
def install_bundled_reverse_apks(serial: str | None = None, packages: list | None = None, reinstall: bool = True, grant: bool = True, timeout: int = 300):
    return hooks.install_bundled_reverse_apks(serial, packages, reinstall, grant, timeout)


@server.tool(
    "bootstrap_device_toolchain",
    "End-to-end no-UI bootstrap: optional adb connect, install AlgorithmAide, push/start bundled patched frida-server, and return health.",
    object_schema(
        {
            "serial": string_prop("Optional adb serial."),
            "tcp_endpoint": string_prop("Optional ADB TCP endpoint, e.g. 192.168.1.10:5555."),
            "install_algorithm_aide_apk": bool_prop("Install bundled AlgorithmAide APK.", True),
            "install_cached_tool_apks": bool_prop("Install all cached reverse-tool APKs.", False),
            "start_frida_server": bool_prop("Start bundled patched frida-server after pushing.", True),
        },
    ),
)
def bootstrap_device_toolchain(
    serial: str | None = None,
    tcp_endpoint: str | None = None,
    install_algorithm_aide_apk: bool = True,
    install_cached_tool_apks: bool = False,
    start_frida_server: bool = True,
):
    return hooks.bootstrap_device_toolchain(serial, tcp_endpoint, install_algorithm_aide_apk, install_cached_tool_apks, start_frida_server)


@server.tool("current_app", "Get current focused app/window from a real device.", object_schema({"serial": string_prop("Optional adb serial.")}))
def current_app(serial: str | None = None):
    return hooks.current_app(serial)


@server.tool(
    "start_app",
    "Start an app package on a real device.",
    object_schema({"package": string_prop("Package name."), "activity": string_prop("Optional activity name."), "serial": string_prop("Optional adb serial.")}, required=["package"]),
)
def start_app(package: str, activity: str | None = None, serial: str | None = None):
    return hooks.start_app(serial, package, activity)


@server.tool(
    "stop_app",
    "Force-stop an app package on a real device.",
    object_schema({"package": string_prop("Package name."), "serial": string_prop("Optional adb serial.")}, required=["package"]),
)
def stop_app(package: str, serial: str | None = None):
    return hooks.stop_app(serial, package)


@server.tool(
    "clear_app",
    "Clear app data on a real device.",
    object_schema({"package": string_prop("Package name."), "serial": string_prop("Optional adb serial.")}, required=["package"]),
)
def clear_app(package: str, serial: str | None = None):
    return hooks.clear_app(serial, package)


@server.tool(
    "install_apk",
    "Install an APK on the real device.",
    object_schema(
        {
            "apk_path": string_prop("APK path, absolute or relative to project root."),
            "serial": string_prop("Optional adb serial."),
            "reinstall": bool_prop("Use adb install -r.", True),
            "grant": bool_prop("Use adb install -g.", True),
        },
        required=["apk_path"],
    ),
)
def install_apk(apk_path: str, serial: str | None = None, reinstall: bool = True, grant: bool = True):
    return hooks.install_apk(serial, apk_path, reinstall, grant)


@server.tool("package_info", "Get installed package version, path and providers.", object_schema({"package": string_prop("Package name."), "serial": string_prop("Optional adb serial.")}, required=["package"]))
def package_info(package: str, serial: str | None = None):
    return hooks.package_info(serial, package)


@server.tool(
    "pull_package_apk",
    "Pull base/split APK files for an installed package into android_mcp/_work/device_apks/<package>.",
    object_schema(
        {
            "package": string_prop("Package name."),
            "serial": string_prop("Optional adb serial."),
            "output_dir": string_prop("Optional local output directory."),
            "timeout": int_prop("Timeout seconds.", 180, 1, 600),
        },
        required=["package"],
    ),
)
def pull_package_apk(package: str, serial: str | None = None, output_dir: str | None = None, timeout: int = 180):
    return hooks.pull_package_apk(serial, package, output_dir, timeout)


@server.tool(
    "analyze_pulled_apks",
    "Run android_mcp/tools/analyze_device_apks.py and summarize pulled APK manifest IPC surfaces.",
    object_schema(
        {
            "root": string_prop("Optional APK repository root."),
            "output": string_prop("Optional output JSON path or filename."),
            "pretty": bool_prop("Pretty-print JSON.", True),
            "timeout": int_prop("Timeout seconds.", 180, 1, 600),
        },
    ),
)
def analyze_pulled_apks(root: str | None = None, output: str | None = None, pretty: bool = True, timeout: int = 180):
    return hooks.analyze_pulled_apks(root, output, pretty, timeout)


@server.tool(
    "package_components",
    "Return structured activities/services/receivers/providers from pulled manifest analysis plus dumpsys excerpt.",
    object_schema(
        {
            "package": string_prop("Package name."),
            "serial": string_prop("Optional adb serial."),
            "include_dump": bool_prop("Include full dumpsys output.", False),
            "timeout": int_prop("Timeout seconds.", 30, 1, 180),
        },
        required=["package"],
    ),
)
def package_components(package: str, serial: str | None = None, include_dump: bool = False, timeout: int = 30):
    return hooks.package_components(serial, package, include_dump, timeout)


@server.tool("list_reverse_apps", "List installed third-party packages likely useful for Android reversing.", object_schema({"serial": string_prop("Optional adb serial.")}))
def list_reverse_apps(serial: str | None = None):
    return hooks.list_reverse_apps(serial)


@server.tool("frida_devices", "List Frida devices.", object_schema({"timeout": int_prop("Timeout seconds.", 10, 1, 60)}))
def frida_devices(timeout: int = 10):
    return hooks.frida_devices(timeout)


@server.tool(
    "frida_ps",
    "Run frida-ps -Uai after checking ADB has a real device.",
    object_schema({"serial": string_prop("Optional adb serial used for real-device validation."), "timeout": int_prop("Timeout seconds.", 20, 1, 120)}),
)
def frida_ps(serial: str | None = None, timeout: int = 20):
    return hooks.frida_ps(serial, timeout)


@server.tool(
    "push_patched_frida_server",
    "Push the bundled patched frida-server from android_mcp/toolchain/device/frida to the real device.",
    object_schema(
        {
            "serial": string_prop("Optional adb serial."),
            "local_path": string_prop("Optional local patched frida-server path."),
            "remote_path": string_prop("Remote path.", "/data/local/tmp/new-server"),
        },
    ),
)
def push_patched_frida_server(serial: str | None = None, local_path: str | None = None, remote_path: str = "/data/local/tmp/new-server"):
    return hooks.push_patched_frida_server(serial, local_path, remote_path)


@server.tool(
    "patched_frida_status",
    "Check patched frida-server file/version/process status.",
    object_schema({"serial": string_prop("Optional adb serial."), "remote_path": string_prop("Remote path.", "/data/local/tmp/new-server")}),
)
def patched_frida_status(serial: str | None = None, remote_path: str = "/data/local/tmp/new-server"):
    return hooks.patched_frida_status(serial, remote_path)


@server.tool(
    "start_patched_frida_server",
    "Start patched frida-server on the real rooted device.",
    object_schema(
        {
            "serial": string_prop("Optional adb serial."),
            "remote_path": string_prop("Remote path.", "/data/local/tmp/new-server"),
            "listen": string_prop("Frida listen address.", "0.0.0.0:27042"),
            "kill_existing": bool_prop("Kill existing frida/new-server processes first.", True),
        },
    ),
)
def start_patched_frida_server(serial: str | None = None, remote_path: str = "/data/local/tmp/new-server", listen: str = "0.0.0.0:27042", kill_existing: bool = True):
    return hooks.start_patched_frida_server(serial, remote_path, listen, kill_existing)


@server.tool("stop_patched_frida_server", "Stop frida/new-server/fs_run processes on the real device.", object_schema({"serial": string_prop("Optional adb serial.")}))
def stop_patched_frida_server(serial: str | None = None):
    return hooks.stop_patched_frida_server(serial)


@server.tool(
    "setup_algorithm_aide",
    "Install/permission/launch the bundled AlgorithmAidePro APK from android_mcp/toolchain/apks.",
    object_schema({"serial": string_prop("Optional adb serial."), "apk_path": string_prop("Optional APK path."), "launch": bool_prop("Launch after install.", True)}),
)
def setup_algorithm_aide(serial: str | None = None, apk_path: str | None = None, launch: bool = True):
    return hooks.setup_algorithm_aide(serial, apk_path, launch)


@server.tool("algorithm_aide_status", "Summarize AlgorithmAidePro, LSPosed and prefs status.", object_schema({"serial": string_prop("Optional adb serial.")}))
def algorithm_aide_status(serial: str | None = None):
    return hooks.algorithm_aide_status(serial)


@server.tool("algorithm_aide_list_prefs", "List AlgorithmAidePro private shared_prefs files.", object_schema({"serial": string_prop("Optional adb serial.")}))
def algorithm_aide_list_prefs(serial: str | None = None):
    return hooks.algorithm_aide_list_prefs(serial)


@server.tool(
    "algorithm_aide_read_pref",
    "Read AlgorithmAidePro private shared_prefs file as hex/text through root.",
    object_schema(
        {
            "pref_name": string_prop("Preference file name, e.g. com.junge.algorithmAidePro_preferences.xml."),
            "serial": string_prop("Optional adb serial."),
            "max_bytes": int_prop("Max bytes to render.", 8192, 1, 1048576),
        },
        required=["pref_name"],
    ),
)
def algorithm_aide_read_pref(pref_name: str, serial: str | None = None, max_bytes: int = 8192):
    return hooks.algorithm_aide_read_pref(serial, pref_name, max_bytes)


@server.tool(
    "algorithm_aide_query_config",
    "Query AlgorithmAidePro exported ConfigProvider: content://algorithmAidePro/<pref> with projection keys.",
    object_schema(
        {
            "pref": string_prop("SharedPreferences logical name/path segment."),
            "keys": array_prop("Projection keys to read.", {"type": "string"}),
            "serial": string_prop("Optional adb serial."),
            "timeout": int_prop("Timeout seconds.", 20, 1, 120),
        },
        required=["pref", "keys"],
    ),
)
def algorithm_aide_query_config(pref: str, keys: list, serial: str | None = None, timeout: int = 20):
    return hooks.algorithm_aide_query_config(serial, pref, keys, timeout)


@server.tool(
    "algorithm_aide_put_config",
    "Write string values to AlgorithmAidePro exported ConfigProvider.",
    object_schema(
        {
            "pref": string_prop("SharedPreferences logical name/path segment."),
            "values": {"type": "object", "description": "String values to write.", "additionalProperties": {"type": "string"}},
            "serial": string_prop("Optional adb serial."),
            "timeout": int_prop("Timeout seconds.", 20, 1, 120),
        },
        required=["pref", "values"],
    ),
)
def algorithm_aide_put_config(pref: str, values: dict, serial: str | None = None, timeout: int = 20):
    return hooks.algorithm_aide_put_config(serial, pref, values, timeout)


@server.tool(
    "content_query",
    "Generic adb content query helper for exported provider IPC experiments.",
    object_schema(
        {
            "uri": string_prop("Content URI."),
            "projection": array_prop("Projection columns.", {"type": "string"}),
            "selection": string_prop("Optional SQL-like where selection."),
            "sort": string_prop("Optional sort order."),
            "serial": string_prop("Optional adb serial."),
            "timeout": int_prop("Timeout seconds.", 20, 1, 120),
        },
        required=["uri"],
    ),
)
def content_query(uri: str, projection: list | None = None, selection: str | None = None, sort: str | None = None, serial: str | None = None, timeout: int = 20):
    return hooks.content_query(serial, uri, projection, selection, sort, timeout)


@server.tool(
    "content_insert",
    "Generic adb content insert helper using string --bind values.",
    object_schema(
        {
            "uri": string_prop("Content URI."),
            "values": STRING_MAP,
            "serial": string_prop("Optional adb serial."),
            "timeout": int_prop("Timeout seconds.", 20, 1, 120),
        },
        required=["uri", "values"],
    ),
)
def content_insert(uri: str, values: dict, serial: str | None = None, timeout: int = 20):
    return hooks.content_insert(serial, uri, values, timeout)


@server.tool(
    "content_update",
    "Generic adb content update helper using string --bind values.",
    object_schema(
        {
            "uri": string_prop("Content URI."),
            "values": STRING_MAP,
            "where": string_prop("Optional where clause."),
            "serial": string_prop("Optional adb serial."),
            "timeout": int_prop("Timeout seconds.", 20, 1, 120),
        },
        required=["uri", "values"],
    ),
)
def content_update(uri: str, values: dict, where: str | None = None, serial: str | None = None, timeout: int = 20):
    return hooks.content_update(serial, uri, values, where, timeout)


@server.tool(
    "content_delete",
    "Generic adb content delete helper.",
    object_schema(
        {
            "uri": string_prop("Content URI."),
            "where": string_prop("Optional where clause."),
            "serial": string_prop("Optional adb serial."),
            "timeout": int_prop("Timeout seconds.", 20, 1, 120),
        },
        required=["uri"],
    ),
)
def content_delete(uri: str, where: str | None = None, serial: str | None = None, timeout: int = 20):
    return hooks.content_delete(serial, uri, where, timeout)


@server.tool(
    "content_call",
    "Generic adb content call helper for exported provider RPC experiments.",
    object_schema(
        {
            "uri": string_prop("Content URI."),
            "method": string_prop("Provider method."),
            "arg": string_prop("Optional arg."),
            "extras": {"type": "object", "description": "String extras.", "additionalProperties": {"type": "string"}},
            "serial": string_prop("Optional adb serial."),
            "timeout": int_prop("Timeout seconds.", 20, 1, 120),
        },
        required=["uri", "method"],
    ),
)
def content_call(uri: str, method: str, arg: str | None = None, extras: dict | None = None, serial: str | None = None, timeout: int = 20):
    return hooks.content_call(serial, uri, method, arg, extras, timeout)


@server.tool(
    "intent_start_activity",
    "Run am start for arbitrary activity/action/data/extras without UI navigation.",
    object_schema(
        {
            "component": string_prop("Optional component, e.g. package/.Activity."),
            "package": string_prop("Optional package restriction."),
            "action": string_prop("Optional intent action."),
            "data_uri": string_prop("Optional data URI."),
            "mime_type": string_prop("Optional MIME type."),
            "categories": array_prop("Intent categories.", {"type": "string"}),
            "extras": STRING_MAP,
            "flags": array_prop("Intent flags as integers/strings.", {"type": "string"}),
            "wait": bool_prop("Use -W and wait for launch.", False),
            "serial": string_prop("Optional adb serial."),
            "timeout": int_prop("Timeout seconds.", 20, 1, 120),
        },
    ),
)
def intent_start_activity(
    component: str | None = None,
    package: str | None = None,
    action: str | None = None,
    data_uri: str | None = None,
    mime_type: str | None = None,
    categories: list | None = None,
    extras: dict | None = None,
    flags: list | None = None,
    wait: bool = False,
    serial: str | None = None,
    timeout: int = 20,
):
    return hooks.intent_start_activity(serial, component, package, action, data_uri, mime_type, categories, extras, flags, wait, timeout)


@server.tool(
    "intent_broadcast",
    "Run am broadcast for exported receivers/actions without UI navigation.",
    object_schema(
        {
            "action": string_prop("Intent action."),
            "component": string_prop("Optional receiver component."),
            "package": string_prop("Optional package restriction."),
            "data_uri": string_prop("Optional data URI."),
            "extras": STRING_MAP,
            "receiver_permission": string_prop("Optional receiver permission."),
            "serial": string_prop("Optional adb serial."),
            "timeout": int_prop("Timeout seconds.", 20, 1, 120),
        },
        required=["action"],
    ),
)
def intent_broadcast(action: str, component: str | None = None, package: str | None = None, data_uri: str | None = None, extras: dict | None = None, receiver_permission: str | None = None, serial: str | None = None, timeout: int = 20):
    return hooks.intent_broadcast(serial, action, component, package, data_uri, extras, receiver_permission, timeout)


@server.tool(
    "intent_start_service",
    "Run am startservice/start-foreground-service for exported service experiments.",
    object_schema(
        {
            "component": string_prop("Optional service component."),
            "package": string_prop("Optional package restriction."),
            "action": string_prop("Optional service action."),
            "data_uri": string_prop("Optional data URI."),
            "extras": STRING_MAP,
            "foreground": bool_prop("Use am start-foreground-service.", False),
            "serial": string_prop("Optional adb serial."),
            "timeout": int_prop("Timeout seconds.", 20, 1, 120),
        },
    ),
)
def intent_start_service(component: str | None = None, package: str | None = None, action: str | None = None, data_uri: str | None = None, extras: dict | None = None, foreground: bool = False, serial: str | None = None, timeout: int = 20):
    return hooks.intent_start_service(serial, component, package, action, data_uri, extras, foreground, timeout)


@server.tool(
    "intent_stop_service",
    "Run am stopservice for a component.",
    object_schema({"component": string_prop("Service component."), "serial": string_prop("Optional adb serial."), "timeout": int_prop("Timeout seconds.", 20, 1, 120)}, required=["component"]),
)
def intent_stop_service(component: str, serial: str | None = None, timeout: int = 20):
    return hooks.intent_stop_service(serial, component, timeout)


@server.tool("lsposed_status", "Summarize LSPosed files, modules and recent logs.", object_schema({"serial": string_prop("Optional adb serial.")}))
def lsposed_status(serial: str | None = None):
    return hooks.lsposed_status(serial)


@server.tool(
    "pull_lsposed_db",
    "Pull and summarize LSPosed modules_config.db.",
    object_schema({"serial": string_prop("Optional adb serial."), "output_dir": string_prop("Optional local output directory.")}),
)
def pull_lsposed_db(serial: str | None = None, output_dir: str | None = None):
    return hooks.pull_lsposed_db(serial, output_dir)


@server.tool(
    "lsposed_query_config",
    "Run a read-only SQL query against /data/adb/lspd/config/modules_config.db after root pull.",
    object_schema(
        {
            "sql": string_prop("Read-only SQL: SELECT/PRAGMA/WITH or .schema.", "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"),
            "serial": string_prop("Optional adb serial."),
            "max_rows": int_prop("Maximum rows.", 200, 1, 2000),
            "timeout": int_prop("Timeout seconds.", 60, 1, 300),
        },
    ),
)
def lsposed_query_config(sql: str = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name", serial: str | None = None, max_rows: int = 200, timeout: int = 60):
    return hooks.lsposed_query_config(serial, sql, max_rows, timeout)


@server.tool("lsposed_list_modules", "Summarize module-like LSPosed DB tables.", object_schema({"serial": string_prop("Optional adb serial."), "timeout": int_prop("Timeout seconds.", 60, 1, 300)}))
def lsposed_list_modules(serial: str | None = None, timeout: int = 60):
    return hooks.lsposed_list_modules(serial, timeout)


@server.tool(
    "lsposed_set_module_enabled",
    "Enable/disable an LSPosed module by editing a pulled DB copy; dry_run defaults true.",
    object_schema(
        {
            "module_package": string_prop("Module package, e.g. com.junge.algorithmAidePro."),
            "enabled": bool_prop("Enable module."),
            "dry_run": bool_prop("Preview only; set false to write DB back.", True),
            "serial": string_prop("Optional adb serial."),
            "timeout": int_prop("Timeout seconds.", 60, 1, 300),
        },
        required=["module_package", "enabled"],
    ),
)
def lsposed_set_module_enabled(module_package: str, enabled: bool, dry_run: bool = True, serial: str | None = None, timeout: int = 60):
    return hooks.lsposed_set_module_enabled(serial, module_package, enabled, dry_run, timeout)


@server.tool(
    "lsposed_set_scope",
    "Add/remove a target package in an LSPosed module scope; dry_run defaults true.",
    object_schema(
        {
            "module_package": string_prop("Module package, e.g. com.junge.algorithmAidePro."),
            "target_package": string_prop("Target app package."),
            "enabled": bool_prop("Add target to scope when true; remove when false.", True),
            "user_id": int_prop("Android user id.", 0, 0, 999),
            "dry_run": bool_prop("Preview only; set false to write DB back.", True),
            "serial": string_prop("Optional adb serial."),
            "timeout": int_prop("Timeout seconds.", 60, 1, 300),
        },
        required=["module_package", "target_package"],
    ),
)
def lsposed_set_scope(module_package: str, target_package: str, enabled: bool = True, user_id: int = 0, dry_run: bool = True, serial: str | None = None, timeout: int = 60):
    return hooks.lsposed_set_scope(serial, module_package, target_package, enabled, user_id, dry_run, timeout)


@server.tool(
    "backup_app_data",
    "Root-backup /data/user/0/<package> to a local tar.gz artifact.",
    object_schema({"package": string_prop("Package name.", "com.junge.algorithmAidePro"), "serial": string_prop("Optional adb serial."), "output_dir": string_prop("Optional output directory.")}),
)
def backup_app_data(package: str = "com.junge.algorithmAidePro", serial: str | None = None, output_dir: str | None = None):
    return hooks.backup_app_data(serial, package, output_dir)


@server.tool(
    "root_ls",
    "List a root-only path through su -c.",
    object_schema({"path": string_prop("Remote path."), "long": bool_prop("Use ls -la.", True), "serial": string_prop("Optional adb serial."), "timeout": int_prop("Timeout seconds.", 20, 1, 120)}, required=["path"]),
)
def root_ls(path: str, long: bool = True, serial: str | None = None, timeout: int = 20):
    return hooks.root_ls(serial, path, long, timeout)


@server.tool(
    "root_read_file",
    "Read a root-only file as text, hex or base64.",
    object_schema(
        {
            "path": string_prop("Remote file path."),
            "max_bytes": int_prop("Max bytes.", 65536, 1, 8388608),
            "mode": string_prop("text, hex, or base64.", "text"),
            "serial": string_prop("Optional adb serial."),
            "timeout": int_prop("Timeout seconds.", 30, 1, 180),
        },
        required=["path"],
    ),
)
def root_read_file(path: str, max_bytes: int = 65536, mode: str = "text", serial: str | None = None, timeout: int = 30):
    return hooks.root_read_file(serial, path, max_bytes, mode, timeout)


@server.tool(
    "root_pull_file",
    "Copy a root-only remote file through /data/local/tmp and pull it locally.",
    object_schema(
        {
            "remote_path": string_prop("Root-only remote path."),
            "output_dir": string_prop("Optional local output directory."),
            "output_name": string_prop("Optional local file name."),
            "serial": string_prop("Optional adb serial."),
            "timeout": int_prop("Timeout seconds.", 120, 1, 600),
        },
        required=["remote_path"],
    ),
)
def root_pull_file(remote_path: str, output_dir: str | None = None, output_name: str | None = None, serial: str | None = None, timeout: int = 120):
    return hooks.root_pull_file(serial, remote_path, output_dir, output_name, timeout)


@server.tool(
    "root_push_file",
    "Push a local file to a root-only remote path through /data/local/tmp.",
    object_schema(
        {
            "local_path": string_prop("Local path, absolute or project-root relative."),
            "remote_path": string_prop("Root-only remote destination."),
            "mode": string_prop("chmod mode.", "644"),
            "owner": string_prop("Optional chown owner:group. If omitted, preserve existing owner when possible."),
            "serial": string_prop("Optional adb serial."),
            "timeout": int_prop("Timeout seconds.", 120, 1, 600),
        },
        required=["local_path", "remote_path"],
    ),
)
def root_push_file(local_path: str, remote_path: str, mode: str = "644", owner: str | None = None, serial: str | None = None, timeout: int = 120):
    return hooks.root_push_file(serial, local_path, remote_path, mode, owner, timeout)


@server.tool(
    "sqlite_query_root",
    "Root-pull a SQLite DB family and run a read-only query locally.",
    object_schema(
        {
            "db_path": string_prop("Remote SQLite database path."),
            "sql": string_prop("Read-only SQL: SELECT/PRAGMA/WITH or .schema."),
            "serial": string_prop("Optional adb serial."),
            "max_rows": int_prop("Maximum rows.", 200, 1, 5000),
            "timeout": int_prop("Timeout seconds.", 60, 1, 600),
        },
        required=["db_path", "sql"],
    ),
)
def sqlite_query_root(db_path: str, sql: str, serial: str | None = None, max_rows: int = 200, timeout: int = 60):
    return hooks.sqlite_query_root(serial, db_path, sql, max_rows, timeout)


@server.tool(
    "algorithm_aide_read_json",
    "Read AlgorithmAidePro target config/AppSwitch/logList JSON without UI.",
    object_schema({"package": string_prop("Target package."), "source": string_prop("system, sdcard, appswitch, or loglist.", "system"), "serial": string_prop("Optional adb serial."), "timeout": int_prop("Timeout seconds.", 30, 1, 180)}, required=["package"]),
)
def algorithm_aide_read_json(package: str, source: str = "system", serial: str | None = None, timeout: int = 30):
    return hooks.algorithm_aide_read_json(serial, package, source, timeout)


@server.tool(
    "algorithm_aide_write_json",
    "Write AlgorithmAidePro target hook config JSON to /data/system/junge/<pkg>/config.json and optional sdcard mirror.",
    object_schema(
        {
            "package": string_prop("Target package."),
            "config": JSON_OBJECT,
            "mirror_sdcard": bool_prop("Also write /sdcard/Android/data/com.junge.algorithmAidePro/files/config/<pkg>.json.", True),
            "serial": string_prop("Optional adb serial."),
            "timeout": int_prop("Timeout seconds.", 60, 1, 300),
        },
        required=["package", "config"],
    ),
)
def algorithm_aide_write_json(package: str, config: dict, mirror_sdcard: bool = True, serial: str | None = None, timeout: int = 60):
    return hooks.algorithm_aide_write_json(serial, package, config, mirror_sdcard, timeout)


@server.tool(
    "algorithm_aide_set_appswitch",
    "Set /data/system/junge/AppSwitch.json for a target package.",
    object_schema({"package": string_prop("Target package."), "enabled": bool_prop("Enable hook/log switch."), "serial": string_prop("Optional adb serial."), "timeout": int_prop("Timeout seconds.", 60, 1, 300)}, required=["package", "enabled"]),
)
def algorithm_aide_set_appswitch(package: str, enabled: bool, serial: str | None = None, timeout: int = 60):
    return hooks.algorithm_aide_set_appswitch(serial, package, enabled, timeout)


@server.tool(
    "algorithm_aide_write_frida_script",
    "Write a JS script to /data/system/junge/<pkg>/frida/<name>.js for AlgorithmAidePro.",
    object_schema({"package": string_prop("Target package."), "name": string_prop("Script file name."), "script": string_prop("JavaScript content."), "serial": string_prop("Optional adb serial."), "timeout": int_prop("Timeout seconds.", 60, 1, 300)}, required=["package", "name", "script"]),
)
def algorithm_aide_write_frida_script(package: str, name: str, script: str, serial: str | None = None, timeout: int = 60):
    return hooks.algorithm_aide_write_frida_script(serial, package, name, script, timeout)


@server.tool(
    "algorithm_aide_log_db_query",
    "Query /sdcard/Android/media/<pkg>/database/algorithmAidePro.db without UI.",
    object_schema({"package": string_prop("Target package."), "sql": string_prop("Read-only SQL.", "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"), "serial": string_prop("Optional adb serial."), "max_rows": int_prop("Maximum rows.", 200, 1, 5000), "timeout": int_prop("Timeout seconds.", 120, 1, 600)}, required=["package"]),
)
def algorithm_aide_log_db_query(package: str, sql: str = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name", serial: str | None = None, max_rows: int = 200, timeout: int = 120):
    return hooks.algorithm_aide_log_db_query(serial, package, sql, max_rows, timeout)


@server.tool("hma_read_config", "Read HideMyApplist /data/user/0/.../files/config.json without UI.", object_schema({"serial": string_prop("Optional adb serial."), "timeout": int_prop("Timeout seconds.", 30, 1, 180)}))
def hma_read_config(serial: str | None = None, timeout: int = 30):
    return hooks.hma_read_config(serial, timeout)


@server.tool(
    "hma_write_config",
    "Write HideMyApplist config.json without UI.",
    object_schema({"config": JSON_OBJECT, "serial": string_prop("Optional adb serial."), "timeout": int_prop("Timeout seconds.", 60, 1, 300)}, required=["config"]),
)
def hma_write_config(config: dict, serial: str | None = None, timeout: int = 60):
    return hooks.hma_write_config(serial, config, timeout)


@server.tool(
    "hma_apply_template_to_scope",
    "Apply HideMyApplist templates to a target package; dry_run defaults true.",
    object_schema(
        {
            "target_package": string_prop("Target app package."),
            "templates": array_prop("Template names, e.g. LH/pjgg.", {"type": "string"}),
            "use_whitelist": bool_prop("Use whitelist mode.", False),
            "exclude_system_apps": bool_prop("Exclude system apps.", True),
            "dry_run": bool_prop("Preview only.", True),
            "serial": string_prop("Optional adb serial."),
            "timeout": int_prop("Timeout seconds.", 60, 1, 300),
        },
        required=["target_package", "templates"],
    ),
)
def hma_apply_template_to_scope(target_package: str, templates: list, use_whitelist: bool = False, exclude_system_apps: bool = True, dry_run: bool = True, serial: str | None = None, timeout: int = 60):
    return hooks.hma_apply_template_to_scope(serial, target_package, templates, use_whitelist, exclude_system_apps, dry_run, timeout)


@server.tool(
    "generate_hook_template",
    "Generate a Frida hook template into projects/<target>/hooks/.",
    object_schema(
        {
            "target": string_prop("Target directory under projects/."),
            "template": string_prop("Template: java_method, crypto, okhttp, system_loadlibrary, register_natives."),
            "class_name": string_prop("Java class name for java_method."),
            "method_name": string_prop("Java method name for java_method."),
            "output": string_prop("Optional output filename under hooks/."),
        },
        required=["target", "template"],
    ),
)
def generate_hook_template(target: str, template: str, class_name: str | None = None, method_name: str | None = None, output: str | None = None):
    return hooks.generate_hook_template(target, template, class_name, method_name, output)


@server.tool(
    "start_frida_hook",
    "Start a Frida hook as a background session on a real USB device.",
    object_schema(
        {
            "target": string_prop("Target directory under projects/."),
            "package": string_prop("Package name."),
            "script_path": string_prop("Hook script path, absolute or relative to target hooks/."),
            "serial": string_prop("Optional adb serial for real-device validation."),
            "spawn": bool_prop("Spawn package with -f; false attaches by name.", True),
            "pid": int_prop("Optional exact process pid to attach to (from frida_ps). Use when the process name differs from the package, e.g. custom ':suffix' processes; ignored when spawn=true.", minimum=1),
        },
        required=["target", "package", "script_path"],
    ),
)
def start_frida_hook(target: str, package: str, script_path: str, serial: str | None = None, spawn: bool = True, pid: int | None = None):
    return hooks.start_frida_hook(target, package, script_path, serial, spawn, pid)


@server.tool("list_frida_sessions", "List saved Frida background sessions for a target.", object_schema({"target": string_prop("Target.")}, required=["target"]))
def list_frida_sessions(target: str):
    return hooks.list_frida_sessions(target)


@server.tool(
    "read_frida_log",
    "Read stdout/stderr tail for a Frida background session.",
    object_schema({"target": string_prop("Target."), "session_id": string_prop("Session id."), "lines": int_prop("Tail lines.", 200, 1, 2000)}, required=["target", "session_id"]),
)
def read_frida_log(target: str, session_id: str, lines: int = 200):
    return hooks.read_frida_log(target, session_id, lines)


@server.tool(
    "stop_frida_session",
    "Stop a Frida background session by taskkill.",
    object_schema({"target": string_prop("Target."), "session_id": string_prop("Session id.")}, required=["target", "session_id"]),
)
def stop_frida_session(target: str, session_id: str):
    return hooks.stop_frida_session(target, session_id)


@server.tool(
    "screenshot_save",
    "Save a real-device screenshot to android_mcp/_work/screenshots.",
    object_schema({"serial": string_prop("Optional adb serial."), "output": string_prop("Optional output filename under screenshots/.")}),
)
def screenshot_save(serial: str | None = None, output: str | None = None):
    return hooks.screenshot_save(serial, output)


@server.tool(
    "ui_dump",
    "Dump current UI XML and return click/text nodes as fallback automation context.",
    object_schema({"serial": string_prop("Optional adb serial."), "output": string_prop("Optional output filename under ui/.")}),
)
def ui_dump(serial: str | None = None, output: str | None = None):
    return hooks.ui_dump(serial, output)


@server.tool(
    "tap",
    "Tap screen coordinates on a real device.",
    object_schema({"x": int_prop("X coordinate.", minimum=0), "y": int_prop("Y coordinate.", minimum=0), "serial": string_prop("Optional adb serial.")}, required=["x", "y"]),
)
def tap(x: int, y: int, serial: str | None = None):
    return hooks.tap(serial, x, y)


@server.tool(
    "swipe",
    "Swipe screen coordinates on a real device.",
    object_schema(
        {
            "x1": int_prop("Start X.", minimum=0),
            "y1": int_prop("Start Y.", minimum=0),
            "x2": int_prop("End X.", minimum=0),
            "y2": int_prop("End Y.", minimum=0),
            "duration_ms": int_prop("Duration milliseconds.", 300, 0, 10000),
            "serial": string_prop("Optional adb serial."),
        },
        required=["x1", "y1", "x2", "y2"],
    ),
)
def swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300, serial: str | None = None):
    return hooks.swipe(serial, x1, y1, x2, y2, duration_ms)


@server.tool(
    "input_text",
    "Type text through adb input.",
    object_schema({"text": string_prop("Text to type."), "serial": string_prop("Optional adb serial.")}, required=["text"]),
)
def input_text(text: str, serial: str | None = None):
    return hooks.input_text(serial, text)


@server.tool(
    "press_key",
    "Send adb keyevent.",
    object_schema({"key": string_prop("Keyevent name or number, e.g. BACK or 4."), "serial": string_prop("Optional adb serial.")}, required=["key"]),
)
def press_key(key: str, serial: str | None = None):
    return hooks.press_key(serial, key)


@server.tool(
    "logcat_tail",
    "Read recent logcat lines, optionally for a package pid.",
    object_schema({"serial": string_prop("Optional adb serial."), "package": string_prop("Optional package name."), "lines": int_prop("Lines.", 200, 1, 5000)}),
)
def logcat_tail(serial: str | None = None, package: str | None = None, lines: int = 200):
    return hooks.logcat_tail(serial, package, lines)


@server.tool("reqable_status", "Summarize Reqable package/proxy/VPN/data status without UI.", object_schema({"serial": string_prop("Optional adb serial.")}))
def reqable_status(serial: str | None = None):
    return hooks.reqable_status(serial)


@server.tool(
    "android_proxy_set",
    "Set Android global HTTP proxy, useful for Reqable/mitm workflows.",
    object_schema({"host": string_prop("Proxy host."), "port": int_prop("Proxy port.", minimum=1, maximum=65535), "serial": string_prop("Optional adb serial."), "timeout": int_prop("Timeout seconds.", 20, 1, 120)}, required=["host", "port"]),
)
def android_proxy_set(host: str, port: int, serial: str | None = None, timeout: int = 20):
    return hooks.android_proxy_set(serial, host, port, timeout)


@server.tool("android_proxy_clear", "Clear Android global HTTP proxy.", object_schema({"serial": string_prop("Optional adb serial."), "timeout": int_prop("Timeout seconds.", 20, 1, 120)}))
def android_proxy_clear(serial: str | None = None, timeout: int = 20):
    return hooks.android_proxy_clear(serial, timeout)


@server.tool(
    "adb_forward",
    "Add or remove adb forward mapping, e.g. tcp:18080 -> tcp:8080.",
    object_schema({"local": string_prop("Local endpoint, e.g. tcp:18080."), "remote": string_prop("Remote endpoint, e.g. tcp:8080."), "remove": bool_prop("Remove local mapping instead of adding.", False), "serial": string_prop("Optional adb serial."), "timeout": int_prop("Timeout seconds.", 20, 1, 120)}, required=["local", "remote"]),
)
def adb_forward(local: str, remote: str, remove: bool = False, serial: str | None = None, timeout: int = 20):
    return hooks.adb_forward(serial, local, remote, remove, timeout)


@server.tool(
    "adb_reverse",
    "Add or remove adb reverse mapping, e.g. tcp:8080 -> tcp:18080.",
    object_schema({"remote": string_prop("Remote endpoint, e.g. tcp:8080."), "local": string_prop("Local endpoint, e.g. tcp:18080."), "remove": bool_prop("Remove remote mapping instead of adding.", False), "serial": string_prop("Optional adb serial."), "timeout": int_prop("Timeout seconds.", 20, 1, 120)}, required=["remote", "local"]),
)
def adb_reverse(remote: str, local: str, remove: bool = False, serial: str | None = None, timeout: int = 20):
    return hooks.adb_reverse(serial, remote, local, remove, timeout)


@server.tool(
    "tcp_probe_device",
    "Probe common TCP ports on the device loopback/network namespace.",
    object_schema({"host": string_prop("Host to probe from device.", "127.0.0.1"), "ports": array_prop("Ports.", {"type": "integer"}), "serial": string_prop("Optional adb serial."), "timeout": int_prop("Timeout seconds.", 30, 1, 180)}),
)
def tcp_probe_device(host: str = "127.0.0.1", ports: list | None = None, serial: str | None = None, timeout: int = 30):
    return hooks.tcp_probe_device(serial, host, ports, timeout)


@server.tool(
    "http_probe_forwarded",
    "Probe a forwarded local HTTP endpoint from the host.",
    object_schema({"url": string_prop("URL, e.g. http://127.0.0.1:18080/status."), "method": string_prop("HTTP method.", "GET"), "headers": STRING_MAP, "body": string_prop("Optional request body."), "timeout": int_prop("Timeout seconds.", 10, 1, 120)}, required=["url"]),
)
def http_probe_forwarded(url: str, method: str = "GET", headers: dict | None = None, body: str | None = None, timeout: int = 10):
    return hooks.http_probe_forwarded(url, method, headers, body, timeout)


@server.tool(
    "generate_frida_rpc_template",
    "Generate a Frida rpc.exports algorithm oracle template under projects/<target>/hooks/.",
    object_schema(
        {
            "target": string_prop("Target directory under projects/."),
            "output": string_prop("Optional output filename under hooks/."),
            "class_name": string_prop("Optional Java class name."),
            "method_name": string_prop("Optional Java method name."),
        },
        required=["target"],
    ),
)
def generate_frida_rpc_template(target: str, output: str | None = None, class_name: str | None = None, method_name: str | None = None):
    return hooks.generate_frida_rpc_template(target, output, class_name, method_name)


@server.tool(
    "frida_rpc_call",
    "One-shot call into a Frida JS rpc.exports method on the real device.",
    object_schema(
        {
            "package": string_prop("Package/process name to attach or spawn."),
            "script_path": string_prop("JS path absolute or relative to project root."),
            "method": string_prop("rpc.exports method name."),
            "args": array_prop("Arguments to pass to RPC method.", {"description": "JSON-serializable argument."}),
            "serial": string_prop("Optional adb serial for real-device validation."),
            "spawn": bool_prop("Spawn package before RPC call.", False),
            "pid": int_prop("Optional exact process pid to attach to (from frida_ps). Use when the process name differs from the package, e.g. custom ':suffix' processes. Overrides name attach; ignored when spawn=true.", minimum=1),
            "timeout": int_prop("Timeout seconds.", 30, 1, 300),
        },
        required=["package", "script_path", "method"],
    ),
)
def frida_rpc_call(package: str, script_path: str, method: str, args: list | None = None, serial: str | None = None, spawn: bool = False, timeout: int = 30, pid: int | None = None):
    return hooks.frida_rpc_call(package, script_path, method, args, serial, spawn, timeout, pid)


if __name__ == "__main__":
    server.run()

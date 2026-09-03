#!/usr/bin/env python3
"""Analyze APK manifests collected under android_mcp/_work/device_apks.

The script is intentionally Windows/PowerShell friendly and has no third-party
Python dependencies.  It prefers text AndroidManifest.xml files produced by
apktool/jadx-style decoding.  When no decoded manifest is available it falls
back to local Android SDK tools such as aapt/aapt2/apkanalyzer if present, and
finally emits a conservative ZIP-based inventory for the APK.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET


ANDROID_NS = "http://schemas.android.com/apk/res/android"
COMPONENT_TAGS = ("activity", "activity-alias", "service", "receiver", "provider")
COMPONENT_BUCKETS = {
    "activity": "activities",
    "activity-alias": "activities",
    "service": "services",
    "receiver": "receivers",
    "provider": "providers",
}
DEFAULT_WORK_DIR = Path(__file__).resolve().parents[1] / "_work" / "device_apks"
DEFAULT_OUTPUT_NAME = "analysis_manifest.json"


def _android_attr(element: ET.Element, name: str) -> str | None:
    return element.get(f"{{{ANDROID_NS}}}{name}") or element.get(f"android:{name}") or element.get(name)


def _munian_sorted_unique(values: Iterable[str | None]) -> list[str]:
    seen: set[str] = set()
    for value in values:
        if value:
            seen.add(value)
    return sorted(seen)


def _bool_or_none(value: str | None) -> bool | None:
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    return None


def _normalize_component_name(package: str | None, name: str | None) -> str | None:
    if not name:
        return None
    if name.startswith(".") and package:
        return f"{package}{name}"
    return name


def _is_probably_text_xml(path: Path) -> bool:
    try:
        sample = path.read_bytes()[:128]
    except OSError:
        return False
    stripped = sample.lstrip()
    return stripped.startswith(b"<") or stripped.startswith(b"\xef\xbb\xbf<")


def _safe_rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _empty_record(package_hint: str | None = None) -> dict[str, Any]:
    return {
        "package": package_hint,
        "apk_files": [],
        "components": {
            "activities": [],
            "services": [],
            "receivers": [],
            "providers": [],
        },
        "exported": [],
        "authorities": [],
        "permission": [],
        "intent_actions": [],
        "data_schemes": [],
        "xposed_meta": [],
        "sources": [],
        "warnings": [],
    }


def _parse_decoded_manifest(manifest_path: Path, root_dir: Path) -> dict[str, Any]:
    tree = ET.parse(manifest_path)
    root = tree.getroot()
    package_name = root.get("package")
    record = _empty_record(package_name)
    record["sources"].append(
        {
            "type": "decoded_manifest",
            "path": _safe_rel(manifest_path, root_dir),
        }
    )

    permissions: list[str | None] = [
        _android_attr(root, "permission"),
        _android_attr(root, "sharedUserId"),
    ]
    actions: list[str | None] = []
    schemes: list[str | None] = []
    authorities: list[str | None] = []
    exported_components: list[str] = []
    xposed_meta: list[dict[str, Any]] = []

    application = root.find("application")
    if application is not None:
        permissions.append(_android_attr(application, "permission"))
        _collect_meta_data(application, "application", package_name, xposed_meta)

    for component in root.iter():
        tag = _strip_namespace(component.tag)
        if tag not in COMPONENT_TAGS:
            continue

        bucket = COMPONENT_BUCKETS[tag]
        raw_name = _android_attr(component, "name")
        name = _normalize_component_name(package_name, raw_name)
        component_exported = _bool_or_none(_android_attr(component, "exported"))
        component_permission = _android_attr(component, "permission")
        component_authorities = _android_attr(component, "authorities")

        component_actions: list[str | None] = []
        component_schemes: list[str | None] = []
        for child in component.iter():
            child_tag = _strip_namespace(child.tag)
            if child_tag == "action":
                component_actions.append(_android_attr(child, "name"))
            elif child_tag == "data":
                component_schemes.append(_android_attr(child, "scheme"))
        actions.extend(component_actions)
        schemes.extend(component_schemes)
        permissions.append(component_permission)
        authorities.append(component_authorities)

        if component_exported:
            exported_components.append(name or raw_name or "")

        entry = {
            "name": name,
            "type": tag,
            "exported": component_exported,
            "permission": component_permission,
            "authorities": component_authorities,
            "intent_actions": _munian_sorted_unique(component_actions),
            "data_schemes": _munian_sorted_unique(component_schemes),
        }
        record["components"][bucket].append(entry)
        _collect_meta_data(component, tag, name, xposed_meta)

    record["exported"] = _munian_sorted_unique(exported_components)
    record["authorities"] = _munian_sorted_unique(_split_authorities(authorities))
    record["permission"] = _munian_sorted_unique(permissions)
    record["intent_actions"] = _munian_sorted_unique(actions)
    record["data_schemes"] = _munian_sorted_unique(schemes)
    record["xposed_meta"] = xposed_meta
    return record


def _strip_namespace(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _split_authorities(values: Iterable[str | None]) -> Iterable[str]:
    for value in values:
        if not value:
            continue
        for item in value.split(";"):
            item = item.strip()
            if item:
                yield item


def _collect_meta_data(
    element: ET.Element,
    owner_type: str,
    owner_name: str | None,
    xposed_meta: list[dict[str, Any]],
) -> None:
    for child in element:
        if _strip_namespace(child.tag) != "meta-data":
            continue
        meta_name = _android_attr(child, "name")
        meta_value = _android_attr(child, "value") or _android_attr(child, "resource")
        joined = f"{meta_name or ''} {meta_value or ''}".lower()
        if "xposed" in joined or "lsposed" in joined or "edxposed" in joined:
            xposed_meta.append(
                {
                    "owner_type": owner_type,
                    "owner_name": owner_name,
                    "name": meta_name,
                    "value": meta_value,
                }
            )


def _find_decoded_manifests(package_dir: Path) -> list[Path]:
    manifests: list[Path] = []
    for path in package_dir.rglob("AndroidManifest.xml"):
        if path.is_file() and _is_probably_text_xml(path):
            manifests.append(path)

    def score(path: Path) -> tuple[int, int, str]:
        parts = {part.lower() for part in path.parts}
        priority = 0
        if "apktool" in parts or "apktool_out" in parts or "manifest" in parts:
            priority -= 10
        if "jadx" in parts or "decompiled" in parts:
            priority -= 5
        return (priority, len(path.parts), str(path).lower())

    return sorted(manifests, key=score)


def _find_apk_files(package_dir: Path) -> list[Path]:
    return sorted((p for p in package_dir.rglob("*.apk") if p.is_file()), key=lambda p: str(p).lower())


def _discover_android_tools() -> dict[str, Path]:
    tools: dict[str, Path] = {}
    for name in ("aapt2", "aapt", "apkanalyzer"):
        found = shutil.which(name)
        if found:
            tools[name] = Path(found)

    sdk_roots = [
        os.environ.get("ANDROID_HOME"),
        os.environ.get("ANDROID_SDK_ROOT"),
        str(Path.home() / "AppData" / "Local" / "Android" / "Sdk"),
    ]
    for sdk_root in filter(None, sdk_roots):
        build_tools = Path(sdk_root) / "build-tools"
        if not build_tools.is_dir():
            continue
        for version_dir in sorted(build_tools.iterdir(), reverse=True):
            if not version_dir.is_dir():
                continue
            for name in ("aapt2.exe", "aapt.exe"):
                tool_path = version_dir / name
                if tool_path.is_file():
                    tools.setdefault(tool_path.stem, tool_path)
    return tools


def _run_tool(args: list[str], timeout: int = 25) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            args,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    return completed.returncode, completed.stdout


def _analyze_apk_with_tools(apk_path: Path, root_dir: Path, tools: dict[str, Path]) -> dict[str, Any] | None:
    laohe_outputs: list[tuple[str, str]] = []
    if "aapt" in tools:
        code, output = _run_tool([str(tools["aapt"]), "dump", "badging", str(apk_path)])
        if code == 0 and output.strip():
            return _parse_aapt_badging(output, apk_path, root_dir)
        laohe_outputs.append(("aapt", output))

    if "aapt2" in tools:
        code, output = _run_tool([str(tools["aapt2"]), "dump", "badging", str(apk_path)])
        if code == 0 and output.strip():
            return _parse_aapt_badging(output, apk_path, root_dir)
        laohe_outputs.append(("aapt2", output))

    if "apkanalyzer" in tools:
        code, output = _run_tool([str(tools["apkanalyzer"]), "manifest", "print", str(apk_path)])
        if code == 0 and output.lstrip().startswith("<"):
            temp_root = ET.fromstring(output)
            return _parse_manifest_root(temp_root, apk_path, root_dir, "apkanalyzer_manifest")
        laohe_outputs.append(("apkanalyzer", output))

    return None


def _parse_aapt_badging(output: str, apk_path: Path, root_dir: Path) -> dict[str, Any]:
    package_match = re.search(r"^package:\s+name='([^']+)'", output, re.MULTILINE)
    record = _empty_record(package_match.group(1) if package_match else apk_path.parent.name)
    record["apk_files"].append(_safe_rel(apk_path, root_dir))
    record["sources"].append({"type": "aapt_badging", "path": _safe_rel(apk_path, root_dir)})

    activity_names = re.findall(r"^(?:launchable-)?activity(?:-alias)?:\s+name='([^']+)'", output, re.MULTILINE)
    service_names = re.findall(r"^service:\s+name='([^']+)'", output, re.MULTILINE)
    receiver_names = re.findall(r"^receiver:\s+name='([^']+)'", output, re.MULTILINE)
    provider_names = re.findall(r"^provider:\s+name='([^']+)'", output, re.MULTILINE)
    permissions = re.findall(r"^(?:uses-)?permission:\s+name='([^']+)'", output, re.MULTILINE)
    actions = re.findall(r"^uses-feature.*name='([^']+)'", output, re.MULTILINE)

    for bucket, names, type_name in (
        ("activities", activity_names, "activity"),
        ("services", service_names, "service"),
        ("receivers", receiver_names, "receiver"),
        ("providers", provider_names, "provider"),
    ):
        for name in _munian_sorted_unique(names):
            record["components"][bucket].append(
                {
                    "name": _normalize_component_name(record["package"], name),
                    "type": type_name,
                    "exported": None,
                    "permission": None,
                    "authorities": None,
                    "intent_actions": [],
                    "data_schemes": [],
                }
            )

    record["permission"] = _munian_sorted_unique(permissions)
    record["intent_actions"] = _munian_sorted_unique(actions)
    return record


def _parse_manifest_root(root: ET.Element, source_path: Path, root_dir: Path, source_type: str) -> dict[str, Any]:
    # Keep this path-free parser separate from the file parser so no temp files are written.
    # Keep this path-free parser separate from the file parser so no temp files are written.
    package_name = root.get("package")
    record = _empty_record(package_name)
    record["sources"].append({"type": source_type, "path": _safe_rel(source_path, root_dir)})

    permissions: list[str | None] = [_android_attr(root, "permission")]
    actions: list[str | None] = []
    schemes: list[str | None] = []
    authorities: list[str | None] = []
    exported_components: list[str] = []
    xposed_meta: list[dict[str, Any]] = []
    application = root.find("application")
    if application is not None:
        permissions.append(_android_attr(application, "permission"))
        _collect_meta_data(application, "application", package_name, xposed_meta)

    for component in root.iter():
        tag = _strip_namespace(component.tag)
        if tag not in COMPONENT_TAGS:
            continue
        bucket = COMPONENT_BUCKETS[tag]
        raw_name = _android_attr(component, "name")
        name = _normalize_component_name(package_name, raw_name)
        exported = _bool_or_none(_android_attr(component, "exported"))
        permission = _android_attr(component, "permission")
        auth = _android_attr(component, "authorities")
        comp_actions = [_android_attr(c, "name") for c in component.iter() if _strip_namespace(c.tag) == "action"]
        comp_schemes = [_android_attr(c, "scheme") for c in component.iter() if _strip_namespace(c.tag) == "data"]
        actions.extend(comp_actions)
        schemes.extend(comp_schemes)
        permissions.append(permission)
        authorities.append(auth)
        if exported:
            exported_components.append(name or raw_name or "")
        record["components"][bucket].append(
            {
                "name": name,
                "type": tag,
                "exported": exported,
                "permission": permission,
                "authorities": auth,
                "intent_actions": _munian_sorted_unique(comp_actions),
                "data_schemes": _munian_sorted_unique(comp_schemes),
            }
        )
        _collect_meta_data(component, tag, name, xposed_meta)
    record["exported"] = _munian_sorted_unique(exported_components)
    record["authorities"] = _munian_sorted_unique(_split_authorities(authorities))
    record["permission"] = _munian_sorted_unique(permissions)
    record["intent_actions"] = _munian_sorted_unique(actions)
    record["data_schemes"] = _munian_sorted_unique(schemes)
    record["xposed_meta"] = xposed_meta
    return record


def _zip_fallback(apk_path: Path, root_dir: Path) -> dict[str, Any]:
    record = _empty_record(apk_path.parent.name)
    record["apk_files"].append(_safe_rel(apk_path, root_dir))
    record["sources"].append({"type": "zip_fallback", "path": _safe_rel(apk_path, root_dir)})
    try:
        with zipfile.ZipFile(apk_path) as zf:
            names = set(zf.namelist())
    except (OSError, zipfile.BadZipFile) as exc:
        record["warnings"].append(f"Could not read APK as ZIP: {exc}")
        return record
    if "AndroidManifest.xml" not in names:
        record["warnings"].append("APK has no AndroidManifest.xml entry")
    else:
        record["warnings"].append(
            "Binary AndroidManifest.xml found, but no decoded manifest or local Android SDK parser was available"
        )
    return record


def _merge_records(base: dict[str, Any], addition: dict[str, Any]) -> dict[str, Any]:
    if not base.get("package") and addition.get("package"):
        base["package"] = addition["package"]
    for key in ("apk_files", "exported", "authorities", "permission", "intent_actions", "data_schemes"):
        base[key] = _munian_sorted_unique([*base.get(key, []), *addition.get(key, [])])
    for bucket in ("activities", "services", "receivers", "providers"):
        existing = {(item.get("name"), item.get("type")) for item in base["components"][bucket]}
        for item in addition["components"][bucket]:
            marker = (item.get("name"), item.get("type"))
            if marker not in existing:
                base["components"][bucket].append(item)
                existing.add(marker)
    base["xposed_meta"].extend(addition.get("xposed_meta", []))
    base["sources"].extend(addition.get("sources", []))
    base["warnings"].extend(addition.get("warnings", []))
    return base


def analyze_apk_file(apk_path: Path, root_dir: Path, tools: dict[str, Path]) -> dict[str, Any]:
    record = _empty_record(apk_path.stem)
    record["apk_files"] = [_safe_rel(apk_path, root_dir)]
    parsed = _analyze_apk_with_tools(apk_path, root_dir, tools)
    if parsed is None:
        parsed = _zip_fallback(apk_path, root_dir)
    _merge_records(record, parsed)
    if not record.get("package"):
        record["package"] = apk_path.stem
    return record


def analyze_package_dir(package_dir: Path, root_dir: Path, tools: dict[str, Path]) -> dict[str, Any]:
    record = _empty_record(package_dir.name)
    apk_files = _find_apk_files(package_dir)
    record["apk_files"] = [_safe_rel(path, root_dir) for path in apk_files]

    manifests = _find_decoded_manifests(package_dir)
    if manifests:
        for manifest in manifests:
            try:
                parsed = _parse_decoded_manifest(manifest, root_dir)
                _merge_records(record, parsed)
            except ET.ParseError as exc:
                record["warnings"].append(f"Could not parse {_safe_rel(manifest, root_dir)}: {exc}")
            except OSError as exc:
                record["warnings"].append(f"Could not read {_safe_rel(manifest, root_dir)}: {exc}")
        return record

    for apk_path in apk_files:
        _merge_records(record, analyze_apk_file(apk_path, root_dir, tools))
    if not apk_files:
        record["warnings"].append("No APK files or decoded AndroidManifest.xml files found")
    return record


def analyze_device_apks(root_dir: Path) -> dict[str, Any]:
    tools = _discover_android_tools()
    root_dir = root_dir.resolve()
    root_dir.mkdir(parents=True, exist_ok=True)
    direct_apks = sorted((p for p in root_dir.glob("*.apk") if p.is_file()), key=lambda p: p.name.lower())
    package_dirs = sorted((p for p in root_dir.iterdir() if p.is_dir()), key=lambda p: p.name.lower())
    packages = [analyze_apk_file(apk_path, root_dir, tools) for apk_path in direct_apks]
    packages.extend(analyze_package_dir(package_dir, root_dir, tools) for package_dir in package_dirs)
    return {
        "schema_version": 1,
        "root": str(root_dir),
        "tool_hints": {name: str(path) for name, path in sorted(tools.items())},
        "package_count": len(packages),
        "packages": packages,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan android_mcp/_work/device_apks and write a static APK manifest analysis JSON file."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_WORK_DIR,
        help=f"APK repository root. Default: {DEFAULT_WORK_DIR}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=f"Output JSON path. Default: <root>/{DEFAULT_OUTPUT_NAME}",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON with indentation.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    root_dir = args.root
    output_path = args.output or (root_dir / DEFAULT_OUTPUT_NAME)
    analysis = analyze_device_apks(root_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True),
        encoding="utf-8",
    )
    print(f"Wrote {output_path}")
    print(f"Packages analyzed: {analysis['package_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

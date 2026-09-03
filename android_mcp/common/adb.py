from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from .paths import bundled_adb_path
from .process import run_command, which_or_env


EMULATOR_HINTS = [
    "emulator",
    "sdk_gphone",
    "sdk_phone",
    "goldfish",
    "ranchu",
    "mumu",
    "nox",
    "ldplayer",
    "bluestacks",
    "vbox",
    "genymotion",
    "netease",
]


@dataclass
class AndroidDevice:
    serial: str
    state: str
    details: Dict[str, str]
    is_real: bool
    reason: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "serial": self.serial,
            "state": self.state,
            "details": self.details,
            "is_real": self.is_real,
            "reason": self.reason,
        }


def adb_path() -> str:
    env_value = os.environ.get("ANDROID_MCP_ADB")
    if env_value:
        return env_value
    bundled = bundled_adb_path()
    if bundled.exists():
        return str(bundled)
    return which_or_env("ANDROID_MCP_ADB", "adb")


def parse_adb_devices(output: str) -> List[AndroidDevice]:
    devices: List[AndroidDevice] = []
    for raw in output.splitlines():
        line = raw.strip()
        if not line or line.lower().startswith("list of devices"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        serial, state = parts[0], parts[1]
        details: Dict[str, str] = {}
        for part in parts[2:]:
            if ":" in part:
                key, value = part.split(":", 1)
                details[key] = value
        is_real, reason = classify_real_device(serial, details)
        devices.append(AndroidDevice(serial, state, details, is_real, reason))
    return devices


def classify_real_device(serial: str, details: Dict[str, str]) -> tuple[bool, str]:
    joined = " ".join([serial, *[f"{k}:{v}" for k, v in details.items()]]).lower()
    if serial.startswith("emulator-"):
        return False, "serial starts with emulator-"
    for hint in EMULATOR_HINTS:
        if hint in joined:
            return False, f"matched emulator hint: {hint}"
    # localhost TCP endpoints are usually emulator/bridge endpoints.
    if re.match(r"^(127\.0\.0\.1|localhost):\d+$", serial, re.I):
        return False, "localhost adb endpoint"
    return True, "no emulator hints detected"


def list_devices(real_only: bool = True, timeout: int = 10) -> List[Dict[str, object]]:
    result = run_command([adb_path(), "devices", "-l"], timeout=timeout)
    if result["returncode"] != 0:
        raise RuntimeError(f"adb devices failed: {result['stderr']}")
    devices = parse_adb_devices(str(result["stdout"]))
    if real_only and os.environ.get("ANDROID_MCP_ALLOW_EMULATOR") != "1":
        devices = [d for d in devices if d.is_real]
    return [d.to_dict() for d in devices]


def choose_real_serial(serial: Optional[str] = None) -> str:
    allow_emulator = os.environ.get("ANDROID_MCP_ALLOW_EMULATOR") == "1"
    all_devices = list_devices(real_only=False)
    if serial:
        for dev in all_devices:
            if dev["serial"] == serial:
                if not dev["is_real"] and not allow_emulator:
                    raise ValueError(f"refusing emulator-like device {serial}: {dev['reason']}")
                return serial
        raise ValueError(f"device serial not found: {serial}")
    real_devices = [dev for dev in all_devices if dev["is_real"]]
    if real_devices:
        return str(real_devices[0]["serial"])
    if allow_emulator and all_devices:
        return str(all_devices[0]["serial"])
    raise ValueError("no real Android device found. Connect a phone or set ANDROID_MCP_ALLOW_EMULATOR=1 for emulator debugging.")


def adb_args(serial: Optional[str] = None) -> List[str]:
    chosen = choose_real_serial(serial)
    return [adb_path(), "-s", chosen]


def adb_args_no_select(serial: str) -> List[str]:
    if not serial:
        raise ValueError("serial is required")
    return [adb_path(), "-s", serial]

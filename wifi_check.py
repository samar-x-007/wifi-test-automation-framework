"""Read current Wi-Fi signal and noise details from macOS System Profiler."""

import json
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Optional, Tuple


@dataclass
class WiFiStatus:
    """Current Wi-Fi association and signal measurements, when available."""

    connected: bool
    signal_dbm: Optional[int]
    noise_dbm: Optional[int]
    error: Optional[str]


def _find_signal_noise(value: Any) -> Optional[Tuple[int, int]]:
    """Find a System Profiler value such as '-50 dBm / -90 dBm'."""
    if isinstance(value, str):
        match = re.search(r"(-?\d+)\s*dBm\s*/\s*(-?\d+)\s*dBm", value, re.IGNORECASE)
        if match:
            return int(match.group(1)), int(match.group(2))
    elif isinstance(value, dict):
        for nested_value in value.values():
            result = _find_signal_noise(nested_value)
            if result:
                return result
    elif isinstance(value, list):
        for nested_value in value:
            result = _find_signal_noise(nested_value)
            if result:
                return result
    return None


def parse_wifi_data(data: dict) -> WiFiStatus:
    """Extract signal/noise values without exposing the network name."""
    try:
        interfaces = data["SPAirPortDataType"][0]["spairport_airport_interfaces"]
    except (KeyError, IndexError, TypeError):
        return WiFiStatus(False, None, None, "System Profiler returned an unexpected Wi-Fi data format.")

    for interface in interfaces:
        current_network = interface.get("spairport_current_network_information")
        if isinstance(current_network, dict):
            measurements = _find_signal_noise(current_network)
            if measurements:
                signal_dbm, noise_dbm = measurements
                return WiFiStatus(True, signal_dbm, noise_dbm, None)
            return WiFiStatus(
                True,
                None,
                None,
                "Wi-Fi is connected, but signal/noise measurements were not available.",
            )

    return WiFiStatus(False, None, None, "Wi-Fi is off or not associated with a network.")


def get_wifi_status() -> WiFiStatus:
    """Read Wi-Fi details using the built-in macOS System Profiler command."""
    try:
        result = subprocess.run(
            ["/usr/sbin/system_profiler", "-json", "-detailLevel", "basic", "SPAirPortDataType"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return WiFiStatus(False, None, None, "System Profiler timed out while reading Wi-Fi details.")
    except FileNotFoundError:
        return WiFiStatus(False, None, None, "Could not find the macOS system_profiler command.")

    if result.returncode != 0:
        detail = result.stderr.strip() or "System Profiler could not read Wi-Fi details."
        return WiFiStatus(False, None, None, detail)

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return WiFiStatus(False, None, None, "System Profiler returned invalid JSON.")

    return parse_wifi_data(data)

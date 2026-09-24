"""Load and validate the framework settings from config.json."""

import json
import math
from pathlib import Path


CONFIG_PATH = Path(__file__).with_name("config.json")
REQUIRED_SETTINGS = {
    "dns_host",
    "ping_host",
    "http_url",
    "max_packet_loss_percent",
    "http_performance_samples",
    "max_average_http_latency_ms",
    "min_wifi_signal_dbm",
}


def load_config(path=CONFIG_PATH):
    """Read settings and raise a clear error if the JSON is incomplete or invalid."""
    try:
        with open(path, encoding="utf-8") as config_file:
            settings = json.load(config_file)
    except FileNotFoundError as error:
        raise ValueError(f"Configuration file not found: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Configuration file is not valid JSON: {error}") from error

    if not isinstance(settings, dict):
        raise ValueError("Configuration must be a JSON object.")

    missing = REQUIRED_SETTINGS - settings.keys()
    unknown = settings.keys() - REQUIRED_SETTINGS
    if missing or unknown:
        details = []
        if missing:
            details.append("missing: " + ", ".join(sorted(missing)))
        if unknown:
            details.append("unknown: " + ", ".join(sorted(unknown)))
        raise ValueError("Invalid configuration keys (" + "; ".join(details) + ").")

    for key in ("dns_host", "ping_host", "http_url"):
        if not isinstance(settings[key], str) or not settings[key].strip():
            raise ValueError(f"'{key}' must be a non-empty string.")

    loss_limit = settings["max_packet_loss_percent"]
    if isinstance(loss_limit, bool) or not isinstance(loss_limit, (int, float)):
        raise ValueError("'max_packet_loss_percent' must be a number from 0 to 100.")
    if not math.isfinite(loss_limit) or not 0 <= loss_limit <= 100:
        raise ValueError("'max_packet_loss_percent' must be a number from 0 to 100.")

    samples = settings["http_performance_samples"]
    if type(samples) is not int or samples < 1:
        raise ValueError("'http_performance_samples' must be a positive whole number.")

    latency_limit = settings["max_average_http_latency_ms"]
    if isinstance(latency_limit, bool) or not isinstance(latency_limit, (int, float)):
        raise ValueError("'max_average_http_latency_ms' must be a positive number.")
    if not math.isfinite(latency_limit) or latency_limit <= 0:
        raise ValueError("'max_average_http_latency_ms' must be a positive number.")

    min_signal = settings["min_wifi_signal_dbm"]
    if type(min_signal) is not int or not -120 <= min_signal <= 0:
        raise ValueError("'min_wifi_signal_dbm' must be a whole number from -120 to 0.")

    return settings

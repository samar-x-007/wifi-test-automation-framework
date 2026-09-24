"""Tests for reading the project's configuration."""

import json
import tempfile
import unittest
from pathlib import Path

from config import load_config


VALID_SETTINGS = {
    "dns_host": "example.com",
    "ping_host": "1.1.1.1",
    "http_url": "https://example.com",
    "max_packet_loss_percent": 25.0,
    "http_performance_samples": 3,
    "max_average_http_latency_ms": 1000.0,
    "min_wifi_signal_dbm": -70,
}


class ConfigTests(unittest.TestCase):
    def load_settings(self, settings):
        temporary_file = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False)
        self.addCleanup(Path(temporary_file.name).unlink, missing_ok=True)
        with temporary_file:
            json.dump(settings, temporary_file)
        return load_config(temporary_file.name)

    def test_loads_valid_settings(self):
        self.assertEqual(self.load_settings(VALID_SETTINGS), VALID_SETTINGS)

    def test_rejects_a_missing_setting(self):
        settings = dict(VALID_SETTINGS)
        del settings["ping_host"]
        with self.assertRaisesRegex(ValueError, "missing: ping_host"):
            self.load_settings(settings)

    def test_rejects_packet_loss_above_100_percent(self):
        settings = dict(VALID_SETTINGS, max_packet_loss_percent=101)
        with self.assertRaisesRegex(ValueError, "0 to 100"):
            self.load_settings(settings)

    def test_rejects_zero_http_samples(self):
        settings = dict(VALID_SETTINGS, http_performance_samples=0)
        with self.assertRaisesRegex(ValueError, "positive whole number"):
            self.load_settings(settings)

    def test_rejects_wifi_threshold_outside_rssi_range(self):
        settings = dict(VALID_SETTINGS, min_wifi_signal_dbm=5)
        with self.assertRaisesRegex(ValueError, "from -120 to 0"):
            self.load_settings(settings)

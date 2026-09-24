"""Checks for report contents and safe rendering of logged text."""

import unittest

from generate_report import render_report


class RenderReportTests(unittest.TestCase):
    def test_report_includes_summary_runs_and_diagnostics(self):
        record = {
            "timestamp_utc": "2026-09-25T00:00:00+00:00",
            "checks_passed": 2,
            "checks_total": 3,
            "dns": {"passed": True, "addresses": ["203.0.113.10"]},
            "ping": {
                "passed": True,
                "received": 3,
                "transmitted": 4,
                "packet_loss_percent": 25.0,
                "average_latency_ms": 369.5,
            },
            "http_performance": {
                "passed": False,
                "average_ms": 1749.8,
                "minimum_ms": 152.4,
                "maximum_ms": 3424.9,
                "sample_latencies_ms": [152.4, 1672.1, 3424.9],
            },
            "wifi": {"connected": True, "signal_dbm": -44, "noise_dbm": -97},
        }

        report = render_report([record])

        self.assertIn("Wi-Fi Test Run Report", report)
        self.assertIn("0 / 1", report)
        self.assertIn("1749.8 ms", report)
        self.assertIn("intermittent delays", report)
        self.assertIn("does not establish the cause", report)

    def test_report_shows_wifi_signal_failure(self):
        record = {
            "checks_passed": 3,
            "checks_total": 4,
            "dns": {"passed": True},
            "ping": {"passed": True},
            "http_performance": {"passed": True},
            "wifi": {
                "passed": False,
                "connected": True,
                "signal_dbm": -78,
                "noise_dbm": -95,
                "minimum_signal_dbm": -70,
            },
        }

        report = render_report([record])

        self.assertIn("Wi-Fi signal failures</span><strong>1</strong>", report)
        self.assertIn("signal -78 / noise -95 dBm; minimum -70 dBm", report)
        self.assertIn('class="badge fail">FAIL</span>', report)

    def test_report_escapes_values_from_run_logs(self):
        record = {
            "dns": {"passed": False},
            "ping": {},
            "http_performance": {},
            "wifi": {"connected": False, "error": "<script>alert(1)</script>"},
        }

        report = render_report([record])

        self.assertNotIn("<script>alert(1)</script>", report)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", report)

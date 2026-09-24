"""Checks for summarizing historical framework results."""

import json
import tempfile
import unittest
from pathlib import Path

from analyze_runs import analyze_records, load_run_records


class AnalyzeRunsTests(unittest.TestCase):
    def test_counts_failures_and_slow_http_runs(self):
        records = [
            {
                "dns": {"passed": True},
                "ping": {"passed": True, "average_latency_ms": 30.0},
                "http_performance": {"passed": True, "average_ms": 120.0},
                "wifi": {"connected": False},
            },
            {
                "dns": {"passed": False},
                "ping": {
                    "passed": True,
                    "average_latency_ms": 369.5,
                    "packet_loss_percent": 25.0,
                },
                "http_performance": {
                    "passed": False,
                    "average_ms": 1500.0,
                    "minimum_ms": 150.0,
                    "maximum_ms": 3400.0,
                    "sample_latencies_ms": [150.0, 950.0, 3400.0],
                },
                "wifi": {"connected": True, "signal_dbm": -44, "noise_dbm": -97},
            },
        ]

        result = analyze_records(records, slow_http_limit_ms=1000.0)

        self.assertEqual(result["total_runs"], 2)
        self.assertEqual(result["failures"], {"dns": 1, "ping": 0, "http_performance": 1, "wifi": 0})
        self.assertEqual(result["slow_http_runs"], [2])
        self.assertEqual(result["average_http_ms"], 810.0)
        self.assertEqual(result["average_ping_ms"], 199.75)
        self.assertEqual(result["wifi_unavailable_runs"], 1)
        self.assertTrue(any("intermittent delays" in note for note in result["diagnoses"]))
        self.assertTrue(any("does not establish the cause" in note for note in result["diagnoses"]))
        self.assertTrue(any("acceptance limit" in note for note in result["diagnoses"]))

    def test_uses_thresholds_saved_with_each_run(self):
        records = [{
            "thresholds": {
                "max_packet_loss_percent": 40.0,
                "max_average_http_latency_ms": 100.0,
            },
            "dns": {"passed": True},
            "ping": {"passed": True, "packet_loss_percent": 0.0, "average_latency_ms": 30.0},
            "http_performance": {
                "passed": False,
                "average_ms": 150.0,
                "minimum_ms": 140.0,
                "maximum_ms": 160.0,
                "sample_latencies_ms": [140.0, 150.0, 160.0],
            },
            "wifi": {
                "connected": True,
                "signal_dbm": -80,
                "minimum_signal_dbm": -70,
            },
        }]

        result = analyze_records(records)

        self.assertEqual(result["slow_http_runs"], [1])
        self.assertEqual(result["failures"]["http_performance"], 1)
        self.assertTrue(any("consistently slow" in note for note in result["diagnoses"]))
        self.assertTrue(any("weak Wi-Fi signal" in note for note in result["diagnoses"]))

    def test_loads_json_lines_and_reports_malformed_rows(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            log_path = Path(temporary_directory) / "run_history.jsonl"
            log_path.write_text('{"run": 1}\nnot json\n', encoding="utf-8")

            records, errors = load_run_records(log_path)

        self.assertEqual(records, [{"run": 1}])
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("line 2:"))


if __name__ == "__main__":
    unittest.main()

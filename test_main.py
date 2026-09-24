"""Offline checks for the combined report and its exit status."""

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import call, patch

import main
from dns_check import DNSResult
from performance_check import PerformanceResult
from ping_check import PingResult
from wifi_check import WiFiStatus


class MainTests(unittest.TestCase):
    def test_repeat_mode_runs_checks_and_waits_between_them(self):
        settings = {"ping_host": "1.1.1.1"}
        with patch("main.sys.argv", ["main.py", "--repeat", "3", "--interval", "2"]):
            with patch("main.load_config", return_value=settings):
                with patch("main.run_check", side_effect=[0, 1, 0]) as run_check:
                    with patch("main.time.sleep") as sleep:
                        with redirect_stdout(io.StringIO()):
                            exit_code = main.main()

        self.assertEqual(exit_code, 1)
        self.assertEqual(run_check.call_count, 3)
        self.assertEqual(sleep.call_args_list, [call(2.0), call(2.0)])

    @patch("main.sys.argv", ["main.py"])
    @patch("main.load_config", side_effect=ValueError("missing ping_host"))
    def test_invalid_config_prints_error_and_stops(self, load_config):
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main.main()

        self.assertEqual(exit_code, 2)
        self.assertIn("Configuration error: missing ping_host", output.getvalue())
        load_config.assert_called_once_with()

    @patch("main.append_run_record")
    @patch("main.ping_host")
    @patch("main.measure_http_performance")
    @patch("main.resolve_host")
    @patch("main.get_wifi_status")
    @patch("main.sys.argv", ["main.py"])
    def test_all_passing_checks_return_zero(
        self, wifi_status, resolve_host, measure_performance, ping_host, append_record
    ):
        resolve_host.return_value = DNSResult(True, ["203.0.113.10"], None)
        ping_host.return_value = PingResult(True, 4, 4, 0.0, 25.0, "ping output")
        measure_performance.return_value = PerformanceResult(3, 3, 0, 80.0, 100.0, 120.0, [80.0, 100.0, 120.0], [])
        wifi_status.return_value = WiFiStatus(True, -52, -88, None)
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main.main()

        self.assertEqual(exit_code, 0)
        self.assertIn("Summary: 4/4 checks passed.", output.getvalue())
        self.assertIn("PASS: signal -52 dBm meets minimum -70 dBm; noise -88 dBm", output.getvalue())
        self.assertEqual(append_record.call_count, 1)
        self.assertEqual(append_record.call_args.args[0]["checks_passed"], 4)
        self.assertTrue(append_record.call_args.args[0]["wifi"]["passed"])
        self.assertEqual(append_record.call_args.args[0]["checks_total"], 4)
        self.assertEqual(
            append_record.call_args.args[0]["thresholds"],
            {"max_packet_loss_percent": 25.0, "max_average_http_latency_ms": 1000.0},
        )

    @patch("main.append_run_record")
    @patch("main.ping_host")
    @patch("main.measure_http_performance")
    @patch("main.resolve_host")
    @patch("main.get_wifi_status")
    @patch("main.sys.argv", ["main.py"])
    def test_weak_wifi_signal_returns_failure(
        self, wifi_status, resolve_host, measure_performance, ping_host, append_record
    ):
        resolve_host.return_value = DNSResult(True, ["203.0.113.10"], None)
        ping_host.return_value = PingResult(True, 4, 4, 0.0, 25.0, "ping output")
        measure_performance.return_value = PerformanceResult(3, 3, 0, 80.0, 100.0, 120.0, [80.0, 100.0, 120.0], [])
        wifi_status.return_value = WiFiStatus(True, -78, -95, None)
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main.main()

        self.assertEqual(exit_code, 1)
        self.assertIn("FAIL: signal -78 dBm is below the required -70 dBm", output.getvalue())
        self.assertIn("Summary: 3/4 checks passed.", output.getvalue())
        self.assertFalse(append_record.call_args.args[0]["wifi"]["passed"])

    @patch("main.append_run_record")
    @patch("main.ping_host")
    @patch("main.measure_http_performance")
    @patch("main.resolve_host")
    @patch("main.get_wifi_status")
    @patch("main.sys.argv", ["main.py"])
    def test_packet_loss_over_limit_returns_failure(
        self, wifi_status, resolve_host, measure_performance, ping_host, append_record
    ):
        resolve_host.return_value = DNSResult(True, ["203.0.113.10"], None)
        ping_host.return_value = PingResult(False, 4, 2, 50.0, 25.0, "50% packet loss")
        measure_performance.return_value = PerformanceResult(3, 3, 0, 80.0, 100.0, 120.0, [80.0, 100.0, 120.0], [])
        wifi_status.return_value = WiFiStatus(False, None, None, "Wi-Fi is off.")
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main.main()

        self.assertEqual(exit_code, 1)
        self.assertIn("Summary: 2/4 checks passed.", output.getvalue())

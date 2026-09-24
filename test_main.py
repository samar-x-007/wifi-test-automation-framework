"""Offline checks for the combined report and its exit status."""

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import main
from dns_check import DNSResult
from performance_check import PerformanceResult
from ping_check import PingResult
from wifi_check import WiFiStatus


class MainTests(unittest.TestCase):
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
        self.assertIn("Summary: 3/3 checks passed.", output.getvalue())
        self.assertIn("signal -52 dBm; noise -88 dBm", output.getvalue())
        self.assertEqual(append_record.call_count, 1)
        self.assertEqual(append_record.call_args.args[0]["checks_passed"], 3)

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
        self.assertIn("Summary: 2/3 checks passed.", output.getvalue())

"""Small offline checks for the ping result handling."""

import unittest
from unittest.mock import patch
import subprocess

from ping_check import ping_host


class PingHostTests(unittest.TestCase):
    @patch("ping_check.subprocess.run")
    def test_successful_ping_returns_pass_and_output(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=["ping"],
            returncode=0,
            stdout=(
                "4 packets transmitted, 4 packets received, 0.0% packet loss\n"
                "round-trip min/avg/max/stddev = 20.0/37.2/54.6/13.8 ms"
            ),
            stderr="",
        )

        result = ping_host("example.com", count=4)

        self.assertTrue(result.reachable)
        self.assertEqual(result.transmitted, 4)
        self.assertEqual(result.received, 4)
        self.assertEqual(result.packet_loss_percent, 0.0)
        self.assertEqual(result.average_latency_ms, 37.2)
        run.assert_called_once_with(
            ["ping", "-c", "4", "example.com"],
            capture_output=True,
            text=True,
            timeout=9,
            check=False,
        )

    @patch("ping_check.subprocess.run")
    def test_failed_ping_returns_fail_and_diagnostic(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=["ping"],
            returncode=2,
            stdout="4 packets transmitted, 0 packets received, 100.0% packet loss",
            stderr="",
        )

        result = ping_host("example.com")

        self.assertFalse(result.reachable)
        self.assertEqual(result.transmitted, 4)
        self.assertEqual(result.received, 0)
        self.assertEqual(result.packet_loss_percent, 100.0)
        self.assertIsNone(result.average_latency_ms)


if __name__ == "__main__":
    unittest.main()

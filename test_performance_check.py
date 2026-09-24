"""Offline checks for repeated HTTP timing and summary calculations."""

import unittest
from unittest.mock import patch

from http_check import HTTPResult
from performance_check import measure_http_performance


class MeasureHTTPPerformanceTests(unittest.TestCase):
    @patch("performance_check.check_http")
    def test_calculates_minimum_average_and_maximum(self, check_http):
        check_http.side_effect = [
            HTTPResult(True, 200, 100.0, None),
            HTTPResult(True, 200, 300.0, None),
            HTTPResult(True, 200, 200.0, None),
        ]

        result = measure_http_performance("https://example.com", samples=3)

        self.assertEqual(result.successful_samples, 3)
        self.assertEqual(result.failed_samples, 0)
        self.assertEqual(result.minimum_ms, 100.0)
        self.assertEqual(result.average_ms, 200.0)
        self.assertEqual(result.maximum_ms, 300.0)
        self.assertEqual(result.sample_latencies_ms, [100.0, 300.0, 200.0])
        self.assertEqual(check_http.call_count, 3)

    @patch("performance_check.check_http")
    def test_counts_failed_requests_without_including_them_in_average(self, check_http):
        check_http.side_effect = [
            HTTPResult(True, 200, 120.0, None),
            HTTPResult(False, None, 5.0, "connection timed out"),
        ]

        result = measure_http_performance("https://example.com", samples=2)

        self.assertEqual(result.successful_samples, 1)
        self.assertEqual(result.failed_samples, 1)
        self.assertEqual(result.average_ms, 120.0)
        self.assertEqual(result.sample_latencies_ms, [120.0, None])
        self.assertEqual(result.errors, ["connection timed out"])

    def test_rejects_zero_samples(self):
        with self.assertRaises(ValueError):
            measure_http_performance("https://example.com", samples=0)

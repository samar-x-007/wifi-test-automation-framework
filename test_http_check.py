"""Offline checks for HTTP response and connection failure handling."""

import urllib.error
import unittest
from unittest.mock import MagicMock, patch

from http_check import check_http


class CheckHTTPTests(unittest.TestCase):
    @patch("http_check.urlopen")
    def test_returns_status_when_server_responds(self, urlopen):
        response = MagicMock()
        response.status = 200
        response.__enter__.return_value = response
        urlopen.return_value = response

        result = check_http("https://example.com")

        self.assertTrue(result.responded)
        self.assertEqual(result.status_code, 200)
        self.assertGreaterEqual(result.elapsed_ms, 0)
        self.assertIsNone(result.error)
        urlopen.assert_called_once_with("https://example.com", timeout=5.0)

    @patch("http_check.urlopen")
    def test_http_error_still_means_server_responded(self, urlopen):
        urlopen.side_effect = urllib.error.HTTPError(
            "https://example.com/missing", 404, "Not Found", {}, None
        )

        result = check_http("https://example.com/missing")

        self.assertTrue(result.responded)
        self.assertEqual(result.status_code, 404)
        self.assertIsNone(result.error)

    @patch("http_check.urlopen")
    def test_connection_error_reports_no_response(self, urlopen):
        urlopen.side_effect = urllib.error.URLError("connection refused")

        result = check_http("https://example.com")

        self.assertFalse(result.responded)
        self.assertIsNone(result.status_code)
        self.assertIn("connection refused", result.error)

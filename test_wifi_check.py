"""Offline checks for Wi-Fi signal parsing and unavailable states."""

import json
import subprocess
import unittest
from unittest.mock import patch

from wifi_check import get_wifi_status, parse_wifi_data


class WiFiCheckTests(unittest.TestCase):
    def test_parses_signal_and_noise_without_returning_network_name(self):
        data = {
            "SPAirPortDataType": [
                {
                    "spairport_airport_interfaces": [
                        {
                            "spairport_current_network_information": {
                                "_name": "<redacted>",
                                "spairport_signal_noise": "-52 dBm / -88 dBm",
                            }
                        }
                    ]
                }
            ]
        }

        result = parse_wifi_data(data)

        self.assertTrue(result.connected)
        self.assertEqual(result.signal_dbm, -52)
        self.assertEqual(result.noise_dbm, -88)
        self.assertIsNone(result.error)
        self.assertNotIn("name", result.__dict__)

    def test_reports_wifi_off_when_there_is_no_current_network(self):
        data = {
            "SPAirPortDataType": [
                {"spairport_airport_interfaces": [{"_name": "en0", "spairport_status_information": "spairport_status_off"}]}
            ]
        }

        result = parse_wifi_data(data)

        self.assertFalse(result.connected)
        self.assertIsNone(result.signal_dbm)
        self.assertIn("off", result.error)

    @patch("wifi_check.subprocess.run")
    def test_reads_json_from_system_profiler(self, run):
        payload = {"SPAirPortDataType": [{"spairport_airport_interfaces": []}]}
        run.return_value = subprocess.CompletedProcess(
            args=["system_profiler"], returncode=0, stdout=json.dumps(payload), stderr=""
        )

        result = get_wifi_status()

        self.assertFalse(result.connected)
        run.assert_called_once_with(
            ["/usr/sbin/system_profiler", "-json", "-detailLevel", "basic", "SPAirPortDataType"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

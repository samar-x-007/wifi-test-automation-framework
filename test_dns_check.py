"""Offline checks for successful and failed DNS lookups."""

import socket
import unittest
from unittest.mock import patch

from dns_check import resolve_host


class ResolveHostTests(unittest.TestCase):
    @patch("dns_check.socket.getaddrinfo")
    def test_returns_unique_addresses(self, getaddrinfo):
        ipv4_record = (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("203.0.113.10", 0))
        ipv6_record = (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("2001:db8::10", 0, 0, 0))
        getaddrinfo.return_value = [ipv4_record, ipv4_record, ipv6_record]

        result = resolve_host("example.com")

        self.assertTrue(result.resolved)
        self.assertEqual(result.addresses, ["203.0.113.10", "2001:db8::10"])
        self.assertIsNone(result.error)

    @patch("dns_check.socket.getaddrinfo")
    def test_returns_dns_error_when_lookup_fails(self, getaddrinfo):
        getaddrinfo.side_effect = socket.gaierror(-2, "name not known")

        result = resolve_host("not-a-real-host.invalid")

        self.assertFalse(result.resolved)
        self.assertEqual(result.addresses, [])
        self.assertIn("name not known", result.error)

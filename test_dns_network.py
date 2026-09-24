"""Live DNS checks using the Mac's configured resolver."""

import pytest

from dns_check import resolve_host


HOST = "example.com"


@pytest.mark.network
def test_public_domain_resolves_to_at_least_one_ip_address():
    result = resolve_host(HOST)

    assert result.resolved, f"Could not resolve {HOST}: {result.error}"
    assert result.addresses

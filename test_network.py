"""Live network checks for the current Wi-Fi connection."""

import pytest

from ping_check import ping_host


HOST = "1.1.1.1"
PING_COUNT = 4
MAX_PACKET_LOSS_PERCENT = 25.0


@pytest.mark.network
def test_internet_host_is_reachable_with_acceptable_packet_loss():
    result = ping_host(HOST, count=PING_COUNT)

    assert result.reachable, f"{HOST} did not respond. Output: {result.output}"
    assert result.transmitted == PING_COUNT
    assert result.packet_loss_percent is not None
    assert result.packet_loss_percent <= MAX_PACKET_LOSS_PERCENT
    assert result.average_latency_ms is not None

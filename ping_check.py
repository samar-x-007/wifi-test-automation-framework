"""Run a basic connectivity check using macOS's ping command."""

import re
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class PingResult:
    """The useful measurements and original output from one ping run."""

    reachable: bool
    transmitted: Optional[int]
    received: Optional[int]
    packet_loss_percent: Optional[float]
    average_latency_ms: Optional[float]
    output: str


def ping_host(host: str, count: int = 4) -> PingResult:
    """Ping a host and return its status and measurements."""
    try:
        result = subprocess.run(
            ["ping", "-c", str(count), host],
            capture_output=True,
            text=True,
            timeout=count + 5,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return PingResult(False, None, None, None, None, f"Ping timed out while checking {host}.")
    except FileNotFoundError:
        return PingResult(False, None, None, None, None, "Could not find the 'ping' command on this Mac.")

    output = result.stdout.strip() or result.stderr.strip()
    stats = re.search(
        r"(?P<sent>\d+) packets transmitted, (?P<received>\d+) packets received, (?P<loss>[\d.]+)% packet loss",
        output,
    )
    latency = re.search(r"round-trip min/avg/max/stddev = [\d.]+/(?P<average>[\d.]+)/", output)

    transmitted = int(stats.group("sent")) if stats else None
    received = int(stats.group("received")) if stats else None
    packet_loss = float(stats.group("loss")) if stats else None
    average_latency = float(latency.group("average")) if latency else None

    return PingResult(
        reachable=result.returncode == 0,
        transmitted=transmitted,
        received=received,
        packet_loss_percent=packet_loss,
        average_latency_ms=average_latency,
        output=output,
    )

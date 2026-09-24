"""Resolve domain names through the Mac's configured DNS resolver."""

import socket
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DNSResult:
    """The IP addresses returned by one DNS lookup, or its error."""

    resolved: bool
    addresses: List[str]
    error: Optional[str]


def resolve_host(host: str) -> DNSResult:
    """Return unique IPv4/IPv6 addresses for a domain name."""
    try:
        records = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        return DNSResult(False, [], str(error))

    addresses = list(dict.fromkeys(record[4][0] for record in records))
    if not addresses:
        return DNSResult(False, [], "DNS returned no IP addresses.")

    return DNSResult(True, addresses, None)

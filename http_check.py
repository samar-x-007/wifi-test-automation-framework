"""Check whether an HTTP service responds and measure its response time."""

import time
import urllib.error
from dataclasses import dataclass
from typing import Optional
from urllib.request import urlopen


@dataclass
class HTTPResult:
    """The response status and timing from one HTTP request."""

    responded: bool
    status_code: Optional[int]
    elapsed_ms: float
    error: Optional[str]


def check_http(url: str, timeout: float = 5.0) -> HTTPResult:
    """Make a GET request and record whether an HTTP response was received."""
    start_time = time.perf_counter()

    try:
        with urlopen(url, timeout=timeout) as response:
            status_code = response.status
    except urllib.error.HTTPError as error:
        # An HTTP error such as 404 still proves that the server responded.
        status_code = error.code
    except (urllib.error.URLError, OSError) as error:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return HTTPResult(False, None, elapsed_ms, str(error))

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    return HTTPResult(True, status_code, elapsed_ms, None)

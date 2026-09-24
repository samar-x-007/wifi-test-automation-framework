"""Measure repeated HTTP response times and summarize their range."""

from dataclasses import dataclass
from statistics import mean
from typing import List, Optional

from http_check import check_http


@dataclass
class PerformanceResult:
    """Response-time statistics for a series of HTTP requests."""

    requested_samples: int
    successful_samples: int
    failed_samples: int
    minimum_ms: Optional[float]
    average_ms: Optional[float]
    maximum_ms: Optional[float]
    sample_latencies_ms: List[Optional[float]]
    errors: List[str]


def measure_http_performance(
    url: str, samples: int = 3, timeout: float = 5.0
) -> PerformanceResult:
    """Request a URL repeatedly and summarize successful response times."""
    if samples <= 0:
        raise ValueError("samples must be greater than zero")

    latencies = []
    sample_latencies = []
    errors = []

    for _ in range(samples):
        result = check_http(url, timeout=timeout)
        has_success_status = (
            result.responded
            and result.status_code is not None
            and 200 <= result.status_code < 400
        )
        if has_success_status:
            latencies.append(result.elapsed_ms)
            sample_latencies.append(result.elapsed_ms)
        else:
            errors.append(result.error or f"HTTP status {result.status_code}")
            sample_latencies.append(None)

    if latencies:
        minimum_ms = min(latencies)
        average_ms = mean(latencies)
        maximum_ms = max(latencies)
    else:
        minimum_ms = average_ms = maximum_ms = None

    return PerformanceResult(
        requested_samples=samples,
        successful_samples=len(latencies),
        failed_samples=len(errors),
        minimum_ms=minimum_ms,
        average_ms=average_ms,
        maximum_ms=maximum_ms,
        sample_latencies_ms=sample_latencies,
        errors=errors,
    )

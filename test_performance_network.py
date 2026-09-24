"""Live repeated HTTP response-time check."""

import pytest

from performance_check import measure_http_performance


URL = "https://example.com"
SAMPLE_COUNT = 3


@pytest.mark.network
def test_example_site_responds_to_all_performance_samples():
    result = measure_http_performance(URL, samples=SAMPLE_COUNT)

    assert result.successful_samples == SAMPLE_COUNT, result.errors
    assert result.minimum_ms is not None
    assert result.average_ms is not None
    assert result.maximum_ms is not None
    assert result.minimum_ms <= result.average_ms <= result.maximum_ms

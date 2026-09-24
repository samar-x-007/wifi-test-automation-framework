"""Live HTTP checks using the current network connection."""

import pytest

from http_check import check_http


URL = "https://example.com"


@pytest.mark.network
def test_example_site_returns_a_success_or_redirect_response():
    result = check_http(URL)

    assert result.responded, f"No HTTP response from {URL}: {result.error}"
    assert result.status_code is not None
    assert 200 <= result.status_code < 400
    assert result.elapsed_ms >= 0

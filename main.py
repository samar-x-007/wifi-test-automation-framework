"""Run the framework's DNS, ping, and HTTP checks in one report."""

import sys
from datetime import datetime, timezone

from dns_check import resolve_host
from log_results import append_run_record
from performance_check import measure_http_performance
from ping_check import ping_host
from wifi_check import get_wifi_status


DEFAULT_DNS_HOST = "example.com"
DEFAULT_PING_HOST = "1.1.1.1"
DEFAULT_HTTP_URL = "https://example.com"
MAX_PACKET_LOSS_PERCENT = 25.0
HTTP_PERFORMANCE_SAMPLES = 3
MAX_AVERAGE_HTTP_LATENCY_MS = 1000.0


def main() -> int:
    ping_target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PING_HOST
    passed = 0
    total = 3

    print("=== DNS ===")
    dns_result = resolve_host(DEFAULT_DNS_HOST)
    if dns_result.resolved:
        print(f"PASS: {DEFAULT_DNS_HOST} resolved to {', '.join(dns_result.addresses)}")
        passed += 1
    else:
        print(f"FAIL: DNS lookup for {DEFAULT_DNS_HOST}: {dns_result.error}")

    print("\n=== Ping ===")
    ping_result = ping_host(ping_target)
    ping_passed = (
        ping_result.reachable
        and ping_result.packet_loss_percent is not None
        and ping_result.packet_loss_percent <= MAX_PACKET_LOSS_PERCENT
    )
    if ping_passed:
        print(
            f"PASS: {ping_target}, {ping_result.received}/{ping_result.transmitted} replies, "
            f"{ping_result.packet_loss_percent}% packet loss, "
            f"average {ping_result.average_latency_ms} ms"
        )
        passed += 1
    else:
        print(f"FAIL: {ping_target} did not meet the ping check. {ping_result.output}")

    print("\n=== HTTP ===")
    performance_result = measure_http_performance(
        DEFAULT_HTTP_URL, samples=HTTP_PERFORMANCE_SAMPLES
    )
    performance_passed = (
        performance_result.successful_samples == HTTP_PERFORMANCE_SAMPLES
        and performance_result.average_ms is not None
        and performance_result.average_ms <= MAX_AVERAGE_HTTP_LATENCY_MS
    )
    if performance_passed:
        print(
            f"PASS: {performance_result.successful_samples}/{HTTP_PERFORMANCE_SAMPLES} requests; "
            f"min/avg/max {performance_result.minimum_ms:.1f}/"
            f"{performance_result.average_ms:.1f}/{performance_result.maximum_ms:.1f} ms"
        )
        passed += 1
    else:
        if performance_result.errors:
            detail = "; ".join(performance_result.errors)
        else:
            detail = (
                f"average latency {performance_result.average_ms:.1f} ms exceeds "
                f"{MAX_AVERAGE_HTTP_LATENCY_MS:.0f} ms"
            )
        print(f"FAIL: {DEFAULT_HTTP_URL}: {detail}")

    print("\n=== Wi-Fi signal ===")
    wifi_result = get_wifi_status()
    if wifi_result.connected and wifi_result.signal_dbm is not None and wifi_result.noise_dbm is not None:
        print(f"INFO: signal {wifi_result.signal_dbm} dBm; noise {wifi_result.noise_dbm} dBm")
    else:
        print(f"INFO: {wifi_result.error or 'Wi-Fi signal measurements are unavailable.'}")

    run_record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "dns": {
            "host": DEFAULT_DNS_HOST,
            "passed": dns_result.resolved,
            "addresses": dns_result.addresses,
            "error": dns_result.error,
        },
        "ping": {
            "host": ping_target,
            "passed": ping_passed,
            "transmitted": ping_result.transmitted,
            "received": ping_result.received,
            "packet_loss_percent": ping_result.packet_loss_percent,
            "average_latency_ms": ping_result.average_latency_ms,
            "error": None if ping_passed else ping_result.output,
        },
        "http_performance": {
            "url": DEFAULT_HTTP_URL,
            "passed": performance_passed,
            "requested_samples": performance_result.requested_samples,
            "successful_samples": performance_result.successful_samples,
            "failed_samples": performance_result.failed_samples,
            "minimum_ms": performance_result.minimum_ms,
            "average_ms": performance_result.average_ms,
            "maximum_ms": performance_result.maximum_ms,
            "sample_latencies_ms": performance_result.sample_latencies_ms,
            "errors": performance_result.errors,
        },
        "wifi": {
            "connected": wifi_result.connected,
            "signal_dbm": wifi_result.signal_dbm,
            "noise_dbm": wifi_result.noise_dbm,
            "error": wifi_result.error,
        },
        "checks_passed": passed,
        "checks_total": total,
    }

    log_saved = True
    try:
        append_run_record(run_record)
        print("\nLog saved: logs/run_history.jsonl")
    except OSError as error:
        log_saved = False
        print(f"\nLog failure: {error}")

    print(f"Summary: {passed}/{total} checks passed.")
    return 0 if passed == total and log_saved else 1


if __name__ == "__main__":
    raise SystemExit(main())

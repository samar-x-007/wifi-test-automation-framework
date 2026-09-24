"""Run the framework's DNS, ping, and HTTP checks in one report."""

import argparse
import math
import sys
import time
from datetime import datetime, timezone

from config import load_config
from dns_check import resolve_host
from log_results import append_run_record
from performance_check import measure_http_performance
from ping_check import ping_host
from wifi_check import get_wifi_status


def run_check(settings: dict, ping_target: str) -> int:
    dns_host = settings["dns_host"]
    http_url = settings["http_url"]
    packet_loss_limit = settings["max_packet_loss_percent"]
    http_samples = settings["http_performance_samples"]
    http_latency_limit = settings["max_average_http_latency_ms"]
    minimum_wifi_signal_dbm = settings["min_wifi_signal_dbm"]

    passed = 0
    total = 4

    print("=== DNS ===")
    dns_result = resolve_host(dns_host)
    if dns_result.resolved:
        print(f"PASS: {dns_host} resolved to {', '.join(dns_result.addresses)}")
        passed += 1
    else:
        print(f"FAIL: DNS lookup for {dns_host}: {dns_result.error}")

    print("\n=== Ping ===")
    ping_result = ping_host(ping_target)
    ping_passed = (
        ping_result.reachable
        and ping_result.packet_loss_percent is not None
        and ping_result.packet_loss_percent <= packet_loss_limit
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
        http_url, samples=http_samples
    )
    performance_passed = (
        performance_result.successful_samples == http_samples
        and performance_result.average_ms is not None
        and performance_result.average_ms <= http_latency_limit
    )
    if performance_passed:
        print(
            f"PASS: {performance_result.successful_samples}/{http_samples} requests; "
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
                f"{http_latency_limit:.0f} ms"
            )
        print(f"FAIL: {http_url}: {detail}")

    print("\n=== Wi-Fi signal ===")
    wifi_result = get_wifi_status()
    wifi_passed = (
        wifi_result.connected
        and wifi_result.signal_dbm is not None
        and wifi_result.signal_dbm >= minimum_wifi_signal_dbm
    )
    if wifi_result.signal_dbm is not None:
        noise_text = (
            f"; noise {wifi_result.noise_dbm} dBm"
            if wifi_result.noise_dbm is not None
            else ""
        )
        if wifi_passed:
            print(
                f"PASS: signal {wifi_result.signal_dbm} dBm meets minimum "
                f"{minimum_wifi_signal_dbm} dBm{noise_text}"
            )
            passed += 1
        else:
            print(
                f"FAIL: signal {wifi_result.signal_dbm} dBm is below the required "
                f"{minimum_wifi_signal_dbm} dBm{noise_text}"
            )
    else:
        print(f"FAIL: {wifi_result.error or 'Wi-Fi signal measurements are unavailable.'}")

    run_record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "thresholds": {
            "max_packet_loss_percent": packet_loss_limit,
            "max_average_http_latency_ms": http_latency_limit,
        },
        "dns": {
            "host": dns_host,
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
            "url": http_url,
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
            "passed": wifi_passed,
            "minimum_signal_dbm": minimum_wifi_signal_dbm,
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Wi-Fi network checks once or repeat them to monitor stability."
    )
    parser.add_argument(
        "ping_target",
        nargs="?",
        help="optional ping target; defaults to the value in config.json",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="number of times to run all checks (default: 1)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=10.0,
        help="seconds to wait between repeated runs (default: 10)",
    )
    args = parser.parse_args()

    if args.repeat < 1:
        parser.error("--repeat must be at least 1")
    if not math.isfinite(args.interval) or args.interval < 0:
        parser.error("--interval must be a finite number that is zero or greater")

    try:
        settings = load_config()
    except ValueError as error:
        print(f"Configuration error: {error}")
        return 2

    ping_target = args.ping_target or settings["ping_host"]
    passed_runs = 0

    for run_number in range(1, args.repeat + 1):
        if args.repeat > 1:
            print(f"\n=== Monitoring run {run_number}/{args.repeat} ===")
        if run_check(settings, ping_target) == 0:
            passed_runs += 1
        if run_number < args.repeat:
            print(f"\nWaiting {args.interval:g} seconds before the next run...")
            time.sleep(args.interval)

    if args.repeat > 1:
        print(f"\nMonitor summary: {passed_runs}/{args.repeat} runs passed.")
    return 0 if passed_runs == args.repeat else 1


if __name__ == "__main__":
    raise SystemExit(main())

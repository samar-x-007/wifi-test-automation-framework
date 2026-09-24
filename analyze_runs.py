"""Summarize failed and slow checks from the saved run history."""

import json
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Tuple

from log_results import LOG_FILE


SLOW_HTTP_LIMIT_MS = 1000.0
PING_MAX_PACKET_LOSS_PERCENT = 25.0


def _diagnose_run(run_number: int, record: Dict[str, Any]) -> List[str]:
    """Describe co-occurring symptoms without claiming a proven root cause."""
    diagnoses = []
    ping = record.get("ping", {})
    http = record.get("http_performance", {})
    wifi = record.get("wifi", {})

    packet_loss = ping.get("packet_loss_percent")
    ping_average = ping.get("average_latency_ms")
    if packet_loss is not None and float(packet_loss) > 0:
        limit_note = (
            f" at the {PING_MAX_PACKET_LOSS_PERCENT:.0f}% acceptance limit"
            if float(packet_loss) == PING_MAX_PACKET_LOSS_PERCENT and ping.get("passed")
            else ""
        )
        diagnoses.append(
            f"Run {run_number}: ping recorded {float(packet_loss):.1f}% packet loss{limit_note}."
        )

    http_average = http.get("average_ms")
    if http_average is not None and float(http_average) > SLOW_HTTP_LIMIT_MS:
        timings = [
            float(value)
            for value in http.get("sample_latencies_ms", [])
            if value is not None
        ]
        if not timings:
            timings = [
                float(value)
                for value in (http.get("minimum_ms"), http.get("maximum_ms"))
                if value is not None
            ]

        if len(timings) >= 2:
            minimum = min(timings)
            maximum = max(timings)
            if maximum - minimum >= 500 or (minimum > 0 and maximum >= minimum * 2):
                diagnoses.append(
                    f"Run {run_number}: HTTP times ranged from {minimum:.1f} to {maximum:.1f} ms; "
                    "the spread suggests intermittent delays."
                )
            else:
                diagnoses.append(
                    f"Run {run_number}: HTTP times were consistently slow, "
                    f"averaging {float(http_average):.1f} ms."
                )
        else:
            diagnoses.append(
                f"Run {run_number}: HTTP average {float(http_average):.1f} ms exceeded "
                f"the {SLOW_HTTP_LIMIT_MS:.0f} ms limit."
            )

        if (packet_loss is not None and float(packet_loss) > 0) or (
            ping_average is not None and float(ping_average) >= 200
        ):
            diagnoses.append(
                f"Run {run_number}: HTTP delay coincided with ping degradation; "
                "this correlation does not establish the cause."
            )
        elif wifi.get("signal_dbm") is not None and int(wifi["signal_dbm"]) <= -70:
            diagnoses.append(
                f"Run {run_number}: slow HTTP also coincided with a weak Wi-Fi signal "
                f"({wifi['signal_dbm']} dBm)."
            )
        else:
            diagnoses.append(
                f"Run {run_number}: ping did not show the same issue; server or HTTP-path "
                "conditions are also possible."
            )

    return diagnoses


def load_run_records(path: Path = LOG_FILE) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Load valid JSON records and report any malformed lines."""
    records = []
    errors = []
    if not path.exists():
        return records, errors

    with path.open(encoding="utf-8") as log_file:
        for line_number, line in enumerate(log_file, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                errors.append(f"line {line_number}: {error.msg}")

    return records, errors


def analyze_records(
    records: List[Dict[str, Any]], slow_http_limit_ms: float = SLOW_HTTP_LIMIT_MS
) -> Dict[str, Any]:
    """Count check failures and summarize available latency measurements."""
    failures = {"dns": 0, "ping": 0, "http_performance": 0}
    slow_http_runs = []
    http_averages = []
    ping_averages = []
    wifi_unavailable = 0
    diagnoses = []

    for run_number, record in enumerate(records, start=1):
        diagnoses.extend(_diagnose_run(run_number, record))
        for component in failures:
            if not record.get(component, {}).get("passed", False):
                failures[component] += 1

        http_average = record.get("http_performance", {}).get("average_ms")
        if http_average is not None:
            http_averages.append(float(http_average))
            if float(http_average) > slow_http_limit_ms:
                slow_http_runs.append(run_number)

        ping_average = record.get("ping", {}).get("average_latency_ms")
        if ping_average is not None:
            ping_averages.append(float(ping_average))

        if not record.get("wifi", {}).get("connected", False):
            wifi_unavailable += 1

    return {
        "total_runs": len(records),
        "failures": failures,
        "slow_http_runs": slow_http_runs,
        "average_http_ms": mean(http_averages) if http_averages else None,
        "average_ping_ms": mean(ping_averages) if ping_averages else None,
        "wifi_unavailable_runs": wifi_unavailable,
        "diagnoses": diagnoses,
    }


def main() -> int:
    records, parse_errors = load_run_records()
    if not records and not parse_errors:
        print(f"No run history found at {LOG_FILE}. Run 'python main.py' first.")
        return 1

    analysis = analyze_records(records)
    print(f"Analyzed {analysis['total_runs']} run(s).")
    for component, count in analysis["failures"].items():
        print(f"{component}: {count} failed run(s)")

    if analysis["average_http_ms"] is not None:
        print(f"Average HTTP response time: {analysis['average_http_ms']:.1f} ms")
    if analysis["average_ping_ms"] is not None:
        print(f"Average ping latency: {analysis['average_ping_ms']:.1f} ms")

    slow_runs = analysis["slow_http_runs"]
    if slow_runs:
        run_list = ", ".join(str(run) for run in slow_runs)
        print(f"Slow HTTP average (over {SLOW_HTTP_LIMIT_MS:.0f} ms): run(s) {run_list}")
    else:
        print(f"Slow HTTP average (over {SLOW_HTTP_LIMIT_MS:.0f} ms): none")

    print(f"Wi-Fi readings unavailable: {analysis['wifi_unavailable_runs']} run(s)")
    if analysis["diagnoses"]:
        print("\nDiagnostics:")
        for diagnosis in analysis["diagnoses"]:
            print(f"- {diagnosis}")
    if analysis["total_runs"] < 2:
        print("Only one run is available; collect more runs before comparing trends.")
    for error in parse_errors:
        print(f"Could not read {error}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

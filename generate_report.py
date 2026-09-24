"""Build a self-contained HTML report from the saved run history."""

from datetime import datetime, timezone
from html import escape
import math
from pathlib import Path
from typing import Any, Dict, List

from analyze_runs import analyze_records, load_run_records
from log_results import LOG_FILE


REPORT_FILE = Path(__file__).resolve().parent / "reports" / "latest_report.html"


def _status_badge(passed: bool) -> str:
    label = "PASS" if passed else "FAIL"
    style = "pass" if passed else "fail"
    return f'<span class="badge {style}">{label}</span>'


def _format_ms(value: Any) -> str:
    return "—" if value is None else f"{float(value):.1f} ms"


def _render_latency_chart(records: List[Dict[str, Any]]) -> str:
    """Render an accessible SVG line chart for ping and HTTP latency."""
    series = {
        "ping": [
            _chart_number(record.get("ping", {}).get("average_latency_ms"))
            for record in records
        ],
        "http": [
            _chart_number(record.get("http_performance", {}).get("average_ms"))
            for record in records
        ],
    }
    available_values = [
        value for values in series.values() for value in values if value is not None
    ]
    if not available_values:
        return '<p class="empty">No latency measurements are available yet.</p>'

    width = 860
    height = 300
    left = 70
    right = 24
    top = 20
    bottom = 48
    plot_width = width - left - right
    plot_height = height - top - bottom
    run_count = len(records)
    step = max(10, math.ceil(max(available_values) / 4 / 10) * 10)
    axis_max = step * 4

    def x_position(index: int) -> float:
        if run_count == 1:
            return left + plot_width / 2
        return left + index * plot_width / (run_count - 1)

    def y_position(value: float) -> float:
        return top + plot_height * (1 - value / axis_max)

    grid = []
    for tick in range(5):
        value = tick * step
        y = y_position(value)
        grid.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" '
            'stroke="#e2e8f0" stroke-width="1"/>'
        )
        grid.append(
            f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" '
            f'class="chart-label">{value:g}</text>'
        )

    x_labels = []
    for index in range(run_count):
        x = x_position(index)
        x_labels.append(
            f'<text x="{x:.1f}" y="{height - 18}" text-anchor="middle" '
            f'class="chart-label">{index + 1}</text>'
        )

    def render_series(name: str, values: List[Any], color: str) -> str:
        fragments = []
        segment = []

        def render_segment(points: List[Any]) -> None:
            if not points:
                return
            coordinates = " ".join(f"{x:.1f},{y:.1f}" for x, y, _, _ in points)
            if len(points) > 1:
                fragments.append(
                    f'<polyline points="{coordinates}" fill="none" stroke="{color}" '
                    'stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
                )
            for x, y, run_number, value in points:
                fragments.append(
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}">'
                    f'<title>Run {run_number}: {name} {value:g} ms</title></circle>'
                )

        for index, value in enumerate(values):
            if value is None:
                render_segment(segment)
                segment = []
            else:
                segment.append(
                    (x_position(index), y_position(value), index + 1, value)
                )
        render_segment(segment)
        return "".join(fragments)

    ping_line = render_series("Ping", series["ping"], "#2563eb")
    http_line = render_series("HTTP", series["http"], "#f97316")
    return (
        f'<div class="chart-legend" aria-hidden="true">'
        '<span><i class="legend-ping"></i>Ping average</span>'
        '<span><i class="legend-http"></i>HTTP average</span></div>'
        f'<svg class="latency-chart" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Average ping and HTTP latency across {run_count} runs">'
        f'<g>{ "".join(grid) }</g>'
        f'<g>{ping_line}{http_line}</g>'
        f'<g>{"".join(x_labels)}</g>'
        f'<text x="{left + plot_width / 2:.1f}" y="{height - 2}" '
        'text-anchor="middle" class="chart-label">Run</text>'
        f'<text transform="translate(18 {top + plot_height / 2:.1f}) rotate(-90)" '
        'text-anchor="middle" class="chart-label">Latency (ms)</text>'
        '</svg>'
    )


def _chart_number(value: Any) -> Any:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def render_report(records: List[Dict[str, Any]]) -> str:
    """Render run summaries, diagnostics, and per-run measurements as HTML."""
    analysis = analyze_records(records)
    total_runs = analysis["total_runs"]
    passed_runs = sum(
        1 for record in records
        if record.get("checks_passed", 0) == record.get("checks_total", 0)
    )

    rows = []
    for run_number, record in enumerate(records, start=1):
        dns = record.get("dns", {})
        ping = record.get("ping", {})
        http = record.get("http_performance", {})
        wifi = record.get("wifi", {})
        timestamp = escape(str(record.get("timestamp_utc", "Unknown")))
        ping_summary = (
            f"{ping.get('received', '—')}/{ping.get('transmitted', '—')} replies; "
            f"{_format_ms(ping.get('average_latency_ms'))}"
        )
        http_range = " / ".join(
            _format_ms(http.get(key)) for key in ("minimum_ms", "average_ms", "maximum_ms")
        )
        wifi_status = (
            _status_badge(bool(wifi["passed"]))
            if "passed" in wifi
            else ""
        )
        wifi_summary = (
            f"signal {wifi.get('signal_dbm')} / noise {wifi.get('noise_dbm')} dBm"
            if wifi.get("signal_dbm") is not None and wifi.get("noise_dbm") is not None
            else str(wifi.get("error") or "Unavailable")
        )
        if wifi.get("minimum_signal_dbm") is not None:
            wifi_summary += f"; minimum {wifi['minimum_signal_dbm']} dBm"
        rows.append(
            "<tr>"
            f"<td>{run_number}<small>{timestamp}</small></td>"
            f"<td>{_status_badge(bool(dns.get('passed')))}</td>"
            f"<td>{_status_badge(bool(ping.get('passed')))}<small>{escape(ping_summary)}</small></td>"
            f"<td>{_status_badge(bool(http.get('passed')))}<small>min / avg / max: {escape(http_range)}</small></td>"
            f"<td>{wifi_status}<small>{escape(wifi_summary)}</small></td>"
            "</tr>"
        )

    if not rows:
        rows.append('<tr><td colspan="5" class="empty">No runs recorded yet.</td></tr>')

    latency_chart = _render_latency_chart(records)
    diagnostics = analysis["diagnoses"]
    if diagnostics:
        diagnosis_items = "".join(f"<li>{escape(note)}</li>" for note in diagnostics)
    else:
        diagnosis_items = "<li>No failure patterns found in the recorded runs.</li>"

    average_http = _format_ms(analysis["average_http_ms"])
    average_ping = _format_ms(analysis["average_ping_ms"])
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    page = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Wi-Fi Test Run Report</title>
  <style>
    :root { color-scheme: light; --ink: #182230; --muted: #5b6878; --line: #dce3ea; --blue: #174ea6; }
    * { box-sizing: border-box; }
    body { margin: 0; background: #f4f7fb; color: var(--ink); font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    main { max-width: 1100px; margin: 36px auto; padding: 0 22px; }
    h1 { margin: 0; font-size: 30px; letter-spacing: -.02em; }
    h2 { margin: 30px 0 12px; font-size: 19px; }
    .subtitle, small { color: var(--muted); }
    .subtitle { margin: 4px 0 22px; }
    .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }
    .card, .panel { background: white; border: 1px solid var(--line); border-radius: 12px; padding: 16px; }
    .card span { display: block; color: var(--muted); font-size: 13px; }
    .card strong { display: block; margin-top: 5px; font-size: 23px; }
    .panel { padding: 0; overflow-x: auto; }
    .chart-panel { padding: 12px; }
    .latency-chart { display: block; width: 100%; min-width: 560px; height: auto; }
    .chart-legend { display: flex; gap: 20px; padding: 4px 10px; color: var(--muted); font-size: 13px; }
    .chart-legend span { display: inline-flex; align-items: center; gap: 7px; }
    .chart-legend i { display: inline-block; width: 10px; height: 10px; border-radius: 50%; }
    .legend-ping { background: #2563eb; }
    .legend-http { background: #f97316; }
    .chart-label { fill: var(--muted); font-size: 12px; }
    table { width: 100%; border-collapse: collapse; min-width: 760px; }
    th, td { padding: 13px 14px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
    th { background: #f8fafc; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
    tr:last-child td { border-bottom: 0; }
    td small { display: block; margin-top: 4px; }
    .badge { display: inline-block; border-radius: 999px; padding: 2px 8px; font-size: 11px; font-weight: 700; }
    .pass { color: #146c43; background: #e4f5ec; }
    .fail { color: #a12622; background: #fde8e7; }
    ul { margin: 0; padding: 2px 0 2px 22px; }
    li + li { margin-top: 8px; }
    .empty { color: var(--muted); text-align: center; }
    footer { color: var(--muted); font-size: 12px; margin-top: 26px; }
  </style>
</head>
<body>
  <main>
    <h1>Wi-Fi Test Run Report</h1>
    <p class="subtitle">Generated {{GENERATED_AT}} from {{TOTAL_RUNS}} saved run(s).</p>
    <section class="cards" aria-label="Run summary">
      <div class="card"><span>Runs with all checks passing</span><strong>{{PASSED_RUNS}} / {{TOTAL_RUNS}}</strong></div>
      <div class="card"><span>DNS failures</span><strong>{{DNS_FAILURES}}</strong></div>
      <div class="card"><span>Ping failures</span><strong>{{PING_FAILURES}}</strong></div>
      <div class="card"><span>HTTP performance failures</span><strong>{{HTTP_FAILURES}}</strong></div>
      <div class="card"><span>Wi-Fi signal failures</span><strong>{{WIFI_FAILURES}}</strong></div>
      <div class="card"><span>Average ping latency</span><strong>{{AVERAGE_PING}}</strong></div>
      <div class="card"><span>Average HTTP response</span><strong>{{AVERAGE_HTTP}}</strong></div>
    </section>
    <h2>Latency across runs</h2>
    <section class="panel chart-panel">{{LATENCY_CHART}}</section>
    <h2>Run details</h2>
    <div class="panel">
      <table>
        <thead><tr><th>Run</th><th>DNS</th><th>Ping</th><th>HTTP min / avg / max</th><th>Wi-Fi signal / noise</th></tr></thead>
        <tbody>{{ROWS}}</tbody>
      </table>
    </div>
    <h2>Diagnostics</h2>
    <section class="panel" style="padding: 16px 20px"><ul>{{DIAGNOSTICS}}</ul></section>
    <footer>Wi-Fi signal passes when it meets the run's configured minimum. Network names are not included. Latency and packet loss vary between runs.</footer>
  </main>
</body>
</html>
"""
    replacements = {
        "{{GENERATED_AT}}": escape(generated_at),
        "{{TOTAL_RUNS}}": str(total_runs),
        "{{PASSED_RUNS}}": str(passed_runs),
        "{{DNS_FAILURES}}": str(analysis["failures"]["dns"]),
        "{{PING_FAILURES}}": str(analysis["failures"]["ping"]),
        "{{HTTP_FAILURES}}": str(analysis["failures"]["http_performance"]),
        "{{WIFI_FAILURES}}": str(analysis["failures"]["wifi"]),
        "{{AVERAGE_PING}}": escape(average_ping),
        "{{AVERAGE_HTTP}}": escape(average_http),
        "{{LATENCY_CHART}}": latency_chart,
        "{{ROWS}}": "\n".join(rows),
        "{{DIAGNOSTICS}}": diagnosis_items,
    }
    for marker, value in replacements.items():
        page = page.replace(marker, value)
    return page


def main() -> int:
    records, parse_errors = load_run_records()
    if not records:
        print(f"No valid run records found in {LOG_FILE}.")
        return 1

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(render_report(records), encoding="utf-8")
    print(f"Report saved to {REPORT_FILE}")
    if parse_errors:
        print(f"Skipped {len(parse_errors)} malformed log line(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

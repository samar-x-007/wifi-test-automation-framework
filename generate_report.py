"""Build a self-contained HTML report from the saved run history."""

from datetime import datetime, timezone
from html import escape
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
        wifi_summary = (
            f"{wifi.get('signal_dbm')} / {wifi.get('noise_dbm')} dBm"
            if wifi.get("signal_dbm") is not None and wifi.get("noise_dbm") is not None
            else str(wifi.get("error") or "Unavailable")
        )
        rows.append(
            "<tr>"
            f"<td>{run_number}<small>{timestamp}</small></td>"
            f"<td>{_status_badge(bool(dns.get('passed')))}</td>"
            f"<td>{_status_badge(bool(ping.get('passed')))}<small>{escape(ping_summary)}</small></td>"
            f"<td>{_status_badge(bool(http.get('passed')))}<small>min / avg / max: {escape(http_range)}</small></td>"
            f"<td>{escape(wifi_summary)}</td>"
            "</tr>"
        )

    if not rows:
        rows.append('<tr><td colspan="5" class="empty">No runs recorded yet.</td></tr>')

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
      <div class="card"><span>Average ping latency</span><strong>{{AVERAGE_PING}}</strong></div>
      <div class="card"><span>Average HTTP response</span><strong>{{AVERAGE_HTTP}}</strong></div>
    </section>
    <h2>Run details</h2>
    <div class="panel">
      <table>
        <thead><tr><th>Run</th><th>DNS</th><th>Ping</th><th>HTTP min / avg / max</th><th>Wi-Fi signal / noise</th></tr></thead>
        <tbody>{{ROWS}}</tbody>
      </table>
    </div>
    <h2>Diagnostics</h2>
    <section class="panel" style="padding: 16px 20px"><ul>{{DIAGNOSTICS}}</ul></section>
    <footer>Wi-Fi values show signal and noise only; network names are not included. Latency and packet loss vary between runs.</footer>
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
        "{{AVERAGE_PING}}": escape(average_ping),
        "{{AVERAGE_HTTP}}": escape(average_http),
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

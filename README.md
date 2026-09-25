# Wi-Fi Network Test Automation Framework

A Python framework for checking DNS resolution, ping connectivity, HTTP response performance, and Wi-Fi signal status on macOS. Each run is saved to a log, and reports can be generated from the results.

## Requirements

- macOS
- Python 3.9 or newer

## Get the project

~~~bash
git clone https://github.com/samar-x-007/wifi-test-automation-framework.git
cd wifi-test-automation-framework
~~~

## Install

From the project folder, create and activate a virtual environment, then install the development dependencies:

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
~~~

## Run a network check

~~~bash
python main.py
~~~

You can optionally provide a ping target for that run:

~~~bash
python main.py 1.1.1.1
~~~

## Monitor connection stability

To run the full set of checks five times, waiting 30 seconds between runs:

~~~bash
python main.py --repeat 5 --interval 30
~~~

Each run is saved separately to the run history. The command returns a failure status if any run fails. You can still give a ping target, for example:

~~~bash
python main.py 8.8.8.8 --repeat 5 --interval 30
~~~

## Change the check settings

Edit config.json to change:

- dns_host: host used for the DNS lookup
- ping_host: default ping target
- http_url: site used for HTTP performance checks
- max_packet_loss_percent: maximum packet loss for a passing ping check
- http_performance_samples: number of HTTP requests to measure
- max_average_http_latency_ms: maximum average HTTP response time for a passing check
- min_wifi_signal_dbm: minimum acceptable Wi-Fi signal strength in dBm; a less-negative reading is stronger

The command-line ping target, when provided, overrides ping_host for that run. A Wi-Fi check passes when signal strength is at least min_wifi_signal_dbm. The program checks the configuration when it starts and reports an error if a setting is invalid. Each saved run records the network thresholds it used, so later analysis can apply the same limits.

## Logs and reports

Each run is appended to logs/run_history.jsonl. To review the run history and generate the HTML report, run:

~~~bash
python analyze_runs.py
python generate_report.py
~~~

Open reports/latest_report.html in a browser.

## Run tests

~~~bash
python -m pytest -v
~~~

Some tests use the network and may depend on your internet connection. To run only the offline tests:

~~~bash
python -m pytest -v -m "not network"
~~~

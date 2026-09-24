"""Checks for appending and reading structured run history."""

import json
import tempfile
import unittest
from pathlib import Path

from log_results import append_run_record


class AppendRunRecordTests(unittest.TestCase):
    def test_appends_each_record_as_a_separate_json_line(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            log_path = Path(temporary_directory) / "logs" / "run_history.jsonl"
            append_run_record({"run": 1, "passed": True}, log_path)
            append_run_record({"run": 2, "passed": False}, log_path)

            records = [json.loads(line) for line in log_path.read_text().splitlines()]

        self.assertEqual(records, [
            {"run": 1, "passed": True},
            {"run": 2, "passed": False},
        ])

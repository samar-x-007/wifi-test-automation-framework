"""Append structured run history as one JSON object per line."""

import json
from pathlib import Path
from typing import Any, Dict, Union


LOG_FILE = Path(__file__).resolve().parent / "logs" / "run_history.jsonl"


def append_run_record(record: Dict[str, Any], path: Union[str, Path] = LOG_FILE) -> None:
    """Append one run record, creating the log folder when needed."""
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(record, sort_keys=True) + "\n")

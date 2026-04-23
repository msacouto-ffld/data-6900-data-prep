"""Mistake log utility (DM-012).

Append-as-you-go markdown log. Each event is appended immediately
so the log persists even on pipeline crash. Privacy: column names
only, never raw data values.

Event types per DM-012:
  handoff_contract_violation, handoff_contract_warning, pii_warning,
  persona_rejection, persona_modification, edge_case_triggered,
  execution_error, verification_correction, verification_issue,
  jargon_scan_flag
"""
from __future__ import annotations

import datetime
import os
from typing import List, Optional


EVENT_TYPES = {
    "handoff_contract_violation",
    "handoff_contract_warning",
    "pii_warning",
    "persona_rejection",
    "persona_modification",
    "edge_case_triggered",
    "execution_error",
    "verification_correction",
    "verification_issue",
    "jargon_scan_flag",
}


def init_mistake_log(log_path: str, run_id: str) -> str:
    """Create the log file with a header. Returns the path."""
    header = (
        f"# Mistake Log\n\n"
        f"**Run ID**: {run_id}\n"
        f"**Generated**: {datetime.datetime.now().isoformat()}\n"
        f"**Events Logged**: 0\n\n---\n"
    )
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(header)
    except Exception as exc:
        print(f"⚠️ Could not create mistake log: {exc}")
    return log_path


def log_event(
    log_path: str,
    event_type: str,
    step: str,
    details: str,
    action: str,
    columns: Optional[List[str]] = None,
) -> None:
    """Append a single event to the log file.

    Never raises — wrapped in try/except so log failures don't
    crash the pipeline.
    """
    if event_type not in EVENT_TYPES:
        print(f"⚠️ Unknown event type: {event_type}")

    # Truncate long strings
    if len(details) > 500:
        details = details[:497] + "..."
    if len(action) > 500:
        action = action[:497] + "..."

    timestamp = datetime.datetime.now().isoformat()
    entry = f"\n### [{timestamp}] {event_type}\n\n"
    entry += f"**Step:** {step}\n"
    entry += f"**Details:** {details}\n"
    entry += f"**Action Taken:** {action}\n"
    if columns:
        entry += f"**Columns Involved:** {', '.join(str(c) for c in columns)}\n"
    entry += "\n---\n"

    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as exc:
        print(f"⚠️ Could not write to mistake log: {exc}")


def count_events(log_path: str) -> int:
    """Count the number of events in the log file."""
    if not os.path.isfile(log_path):
        return 0
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content.count("### [")
    except Exception:
        return 0


if __name__ == "__main__":
    import tempfile
    path = os.path.join(tempfile.gettempdir(), "test-mistake-log.md")
    init_mistake_log(path, "feature-20260414-test-0000")
    log_event(path, "pii_warning", "scan_pii",
              "Column 'email' flagged as direct PII",
              "LLM will note PII in proposals", columns=["email"])
    log_event(path, "persona_rejection", "batch_3",
              "Feature avg_sale rejected as redundant",
              "Alternative not proposed; feature dropped",
              columns=["account_id", "sale_amount"])
    print(f"Events logged: {count_events(path)}")
    with open(path) as f:
        print(f.read())
    os.remove(path)

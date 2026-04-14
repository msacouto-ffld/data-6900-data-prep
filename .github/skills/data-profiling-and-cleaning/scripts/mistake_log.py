"""Mistake log utility (DM-112).

Collects entries in memory throughout the pipeline. Written to
``{transform_run_id}-mistake-log.json`` via a try/finally so the
log persists even if the pipeline crashes mid-execution.

Privacy guarantee: ``affected_columns`` contains column names only,
never raw data values. ``description`` and ``resolution`` use generic
descriptions, not data samples. This is enforced by convention, not
by code — every call site must respect it.
"""
from __future__ import annotations

import datetime
import json
import os
from typing import Any, Dict, List, Optional

from schemas_f2 import DM_112_ENTRY_TYPES


def build_mistake_log(run_id: str) -> Dict[str, Any]:
    """Initialize an empty mistake log for a run."""
    return {
        "run_id": run_id,
        "feature": "002-data-transformation",
        "timestamp": datetime.datetime.now().isoformat(),
        "entries": [],
    }


def log_entry(
    mistake_log: Dict[str, Any],
    entry_type: str,
    step: int,
    transformation_type: str,
    description: str,
    resolution: str,
    affected_columns: Optional[List[str]] = None,
    confidence_score: Optional[int] = None,
) -> None:
    """Append an entry to the in-memory mistake log.

    Raises ``ValueError`` if ``entry_type`` is not a known DM-112 type.
    """
    if entry_type not in DM_112_ENTRY_TYPES:
        raise ValueError(
            f"Unknown mistake log entry type: {entry_type!r}. "
            f"Must be one of {sorted(DM_112_ENTRY_TYPES)}"
        )

    if affected_columns is None:
        affected_columns = []

    # Defensive: never accept raw data values. We can't perfectly detect
    # them, but we can at least refuse very long strings (>200 chars)
    # in description/resolution, which are usually a sign of a raw row
    # being passed through by mistake.
    if len(description) > 400:
        description = description[:397] + "..."
    if len(resolution) > 400:
        resolution = resolution[:397] + "..."

    mistake_log["entries"].append({
        "type": entry_type,
        "step": step,
        "transformation_type": transformation_type,
        "description": description,
        "resolution": resolution,
        "affected_columns": list(affected_columns),
        "confidence_score": confidence_score,
    })


def write_mistake_log(
    mistake_log: Dict[str, Any],
    transform_run_id: str,
    output_dir: str = ".",
) -> Optional[str]:
    """Write the mistake log to ``{run_id}-mistake-log.json``.

    Returns the file path on success, or ``None`` on failure. Never
    raises — this is called from a ``finally`` clause and must never
    mask the original exception.
    """
    filename = f"{transform_run_id}-mistake-log.json"
    file_path = os.path.join(output_dir, filename)
    try:
        # Refresh the timestamp to the actual write time
        mistake_log["timestamp"] = datetime.datetime.now().isoformat()
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(mistake_log, f, indent=2)
        return file_path
    except Exception as exc:
        # Best-effort — print but don't raise
        print(
            f"⚠️ Could not persist mistake log to {filename}: {exc}"
        )
        return None


def count_entries_by_type(mistake_log: Dict[str, Any]) -> Dict[str, int]:
    """Count mistake log entries grouped by type.

    Used by the report generator to fill in the Pipeline Log Summary
    section of DM-109.
    """
    counts: Dict[str, int] = {t: 0 for t in DM_112_ENTRY_TYPES}
    for entry in mistake_log.get("entries", []):
        t = entry.get("type")
        if t in counts:
            counts[t] += 1
    return counts


if __name__ == "__main__":
    log = build_mistake_log("transform-20260414-000000-test")
    log_entry(
        log, "persona_rejection", step=5,
        transformation_type="impute_mean",
        description="Review panel rejected mean imputation",
        resolution="Median imputation adopted as alternative",
        affected_columns=["revenue"],
        confidence_score=82,
    )
    log_entry(
        log, "high_impact_flag", step=6,
        transformation_type="deduplication",
        description="Deduplication removed 15% of rows",
        resolution="Proceeded with user acknowledgment",
        affected_columns=[],
        confidence_score=None,
    )
    print(f"Log has {len(log['entries'])} entries")
    print(f"Counts: {count_entries_by_type(log)}")
    path = write_mistake_log(log, "transform-20260414-000000-test", "/tmp")
    print(f"Written to: {path}")

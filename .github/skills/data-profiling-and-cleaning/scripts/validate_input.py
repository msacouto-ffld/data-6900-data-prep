"""Stage 2 — Validate input CSV.

Runs the 8-check validation sequence, generates the run ID, and returns
the ``validation_result`` dict (DM-002) consumed by all downstream stages.

Runs BEFORE stage 1 is needed — uses only pre-installed pandas — so users
get fast feedback on file problems before the ydata-profiling install runs.

Contract: ``contracts/validate-input.md``
"""
from __future__ import annotations

import datetime
import os
from typing import Any, Dict, Tuple

import pandas as pd

from run_id import generate_run_id

CELL_HARD_LIMIT = 500_000
CELL_WARN_LIMIT = 100_000


class ValidationError(Exception):
    """Hard-gate validation failure. Caller should halt the pipeline."""


def validate_input(file_path: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Validate the uploaded CSV and return (DataFrame, validation_result).

    Parameters
    ----------
    file_path:
        Absolute path to the uploaded CSV in the Claude.ai sandbox.

    Returns
    -------
    tuple
        ``(df, validation_result)`` where ``validation_result`` matches DM-002.

    Raises
    ------
    ValidationError
        If any hard gate fails. The exception message is the
        user-facing error string from the contract.
    """
    print("🔍 Validating your dataset...")

    warnings: list[str] = []

    # Step 1 — file exists and is readable
    if not os.path.isfile(file_path):
        raise ValidationError("File not found or not readable.")
    if not os.access(file_path, os.R_OK):
        raise ValidationError("File not found or not readable.")

    filename = os.path.basename(file_path)

    # Step 2 — extension (informational only)
    if not filename.lower().endswith(".csv"):
        warnings.append(
            f"File extension is not .csv ({filename}). "
            "Proceeding — parser will decide."
        )

    # Step 3 — parses via pd.read_csv (hard gate, FR-002)
    try:
        df = pd.read_csv(file_path)
    except Exception:
        raise ValidationError(
            "This file is not a valid CSV. "
            "Please check the file format and try again."
        )

    # Step 3b — prose detection. pandas is lenient: a text file with
    # no commas is parsed as a 1-column DataFrame where each row is a
    # sentence. The contract requires "not a valid CSV" rejection for
    # prose, so apply a narrow heuristic: if exactly 1 column AND that
    # column's values average >40 characters with word separators,
    # this is almost certainly prose, not data.
    if df.shape[1] == 1:
        col = df.iloc[:, 0].dropna().astype(str)
        if len(col) > 0:
            avg_len = col.str.len().mean()
            # A data column rarely averages >40 chars per value; prose does
            has_spaces = col.str.contains(" ").mean() > 0.5
            if avg_len > 40 and has_spaces:
                raise ValidationError(
                    "This file is not a valid CSV. "
                    "Please check the file format and try again."
                )

    # Step 4 — ≥1 column
    if df.shape[1] < 1:
        raise ValidationError(
            "This CSV has no columns. "
            "Please upload a file with at least one column and one row of data."
        )

    # Step 5 — ≥1 data row (hard gate, FR-003)
    if df.shape[0] < 1:
        raise ValidationError(
            "This CSV contains headers but no data rows. "
            "Please upload a file with at least one row of data."
        )

    row_count = int(df.shape[0])
    column_count = int(df.shape[1])
    cell_count = row_count * column_count

    # Step 6 — cell count ≤ 500,000 (hard gate)
    if cell_count > CELL_HARD_LIMIT:
        raise ValidationError(
            f"This dataset exceeds the profiling limit for Claude.ai "
            f"({cell_count} cells). Reduce rows or columns and re-upload."
        )

    # Step 7 — cell count 100K–500K (warning, proceeds)
    if cell_count >= CELL_WARN_LIMIT:
        warnings.append(
            f"This dataset is large ({cell_count} cells). "
            "Profiling may be slow or incomplete. "
            "Consider uploading a sample."
        )

    # Step 8 — single-row warning (FR-013, proceeds)
    is_single_row = row_count == 1
    if is_single_row:
        warnings.append(
            "This dataset has only one row — some statistics "
            "will be marked as not meaningful."
        )

    run_id = generate_run_id(prefix="profile")
    validation_result: Dict[str, Any] = {
        "run_id": run_id,
        "filename": filename,
        "file_path": file_path,
        "row_count": row_count,
        "column_count": column_count,
        "cell_count": cell_count,
        "is_single_row": is_single_row,
        "warnings": warnings,
        "validated_at": datetime.datetime.now().isoformat(),
    }

    print(f"✅ File: {filename} — valid CSV")
    print(
        f"✅ Shape: {row_count} rows × {column_count} columns "
        f"({cell_count} cells)"
    )
    print("✅ File size: within profiling limits")
    print(f"✅ Run ID: {run_id}")
    for w in warnings:
        print(f"ℹ️ {w}")
    print("\nAll checks passed. Starting profiling...\n")

    return df, validation_result


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python validate_input.py <path-to-csv>")
        sys.exit(1)
    try:
        df, result = validate_input(sys.argv[1])
        print("\nValidation result:")
        for k, v in result.items():
            print(f"  {k}: {v}")
    except ValidationError as e:
        print(f"❌ {e}")
        sys.exit(1)

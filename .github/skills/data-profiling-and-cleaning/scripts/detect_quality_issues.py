"""Stage 3 — Detect data quality issues.

Runs four independent pandas-based checks with no ydata-profiling dependency:

- Duplicate column names (FR-009)
- Special characters in column names (FR-010)
- All-missing columns (FR-011)
- Mixed types within a column (FR-012)

Returns ``quality_detections`` (DM-003) — informational only, never halts
the pipeline on findings.

Contract: ``contracts/detect-quality-issues.md``
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

import pandas as pd

# Valid Python identifier: letter/underscore start, alphanumeric/underscore body
VALID_COLUMN_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

CHECK_NAMES = {
    "duplicate_column_names": "Duplicate column names",
    "special_characters": "Column names with special characters",
    "all_missing_columns": "All-missing columns",
    "mixed_types": "Mixed types within columns",
}


class QualityCheckError(Exception):
    """Raised on internal errors (not on detections)."""


def detect_quality_issues(
    df: pd.DataFrame,
    validation_result: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Run all four quality checks. Return DM-003 list."""
    if df is None or df.empty:
        raise QualityCheckError(
            "Pipeline error: no DataFrame available for quality checks. "
            "Re-run from the beginning."
        )

    print("🔍 Running data quality checks...")

    detections: List[Dict[str, Any]] = []

    # --- Check 1: duplicate column names (FR-009) ---
    dup_mask = df.columns.duplicated()
    if dup_mask.any():
        dup_names = sorted(set(df.columns[dup_mask].tolist()))
        detections.append({
            "check": "duplicate_column_names",
            "status": "found",
            "affected_columns": dup_names,
            "details": (
                f"{len(dup_names)} column name(s) appear more than once: "
                f"{', '.join(dup_names)}. Duplicate column names cause "
                "ambiguous column references and must be resolved before "
                "cleaning."
            ),
        })
    else:
        detections.append({
            "check": "duplicate_column_names",
            "status": "clean",
            "affected_columns": [],
            "details": "No duplicate column names.",
        })

    # --- Check 2: special characters in column names (FR-010) ---
    special_cols = [
        col for col in df.columns
        if not VALID_COLUMN_NAME_RE.match(str(col))
    ]
    if special_cols:
        detections.append({
            "check": "special_characters",
            "status": "found",
            "affected_columns": special_cols,
            "details": (
                f"{len(special_cols)} column name(s) contain special "
                f"characters, spaces, or non-ASCII characters: "
                f"{', '.join(repr(c) for c in special_cols)}. "
                "These will need to be standardized (snake_case) before "
                "downstream processing."
            ),
        })
    else:
        detections.append({
            "check": "special_characters",
            "status": "clean",
            "affected_columns": [],
            "details": "All column names are standard identifiers.",
        })

    # --- Check 3: all-missing columns (FR-011) ---
    all_missing = df.columns[df.isnull().all()].tolist()
    if all_missing:
        detections.append({
            "check": "all_missing_columns",
            "status": "found",
            "affected_columns": all_missing,
            "details": (
                f"{len(all_missing)} column(s) are entirely empty "
                f"(100% missing values): {', '.join(all_missing)}. "
                "These columns contribute no information and should be "
                "dropped."
            ),
        })
    else:
        detections.append({
            "check": "all_missing_columns",
            "status": "clean",
            "affected_columns": [],
            "details": "No columns are entirely empty.",
        })

    # --- Check 4: mixed types (FR-012) ---
    # Per contract: df.apply(lambda col: col.dropna().map(type).nunique() > 1)
    # Drop NaN first to avoid counting NoneType as a distinct type.
    mixed_mask = df.apply(
        lambda col: col.dropna().map(type).nunique() > 1
    )
    mixed_cols = df.columns[mixed_mask].tolist()
    if mixed_cols:
        # Build a type breakdown per column for the details string
        type_breakdowns = []
        for col in mixed_cols:
            types = sorted({t.__name__ for t in df[col].dropna().map(type)})
            type_breakdowns.append(f"{col} ({', '.join(types)})")
        detections.append({
            "check": "mixed_types",
            "status": "found",
            "affected_columns": mixed_cols,
            "details": (
                f"{len(mixed_cols)} column(s) contain more than one Python "
                f"type: {'; '.join(type_breakdowns)}. Mixed types signal "
                "inconsistent encoding and must be resolved before "
                "statistical analysis."
            ),
        })
    else:
        detections.append({
            "check": "mixed_types",
            "status": "clean",
            "affected_columns": [],
            "details": "All columns have consistent types.",
        })

    # --- Console summary ---
    found = [d for d in detections if d["status"] == "found"]
    clean = [d for d in detections if d["status"] == "clean"]

    if found:
        for d in found:
            label = CHECK_NAMES[d["check"]]
            n = len(d["affected_columns"])
            preview = ", ".join(repr(c) for c in d["affected_columns"][:3])
            more = "" if n <= 3 else f" (+{n - 3} more)"
            print(f"⚠️ {label}: {n} column(s) — {preview}{more}")
        if clean:
            clean_names = ", ".join(CHECK_NAMES[d["check"]] for d in clean)
            print(
                f"✅ {len(clean)} of 4 checks passed with no issues "
                f"({clean_names})"
            )
        print("\nData quality checks complete. Running full profiling...\n")
    else:
        print("✅ All 4 data quality checks passed — no issues found.")
        print("\nRunning full profiling...\n")

    return detections


if __name__ == "__main__":
    import sys
    from validate_input import validate_input

    if len(sys.argv) != 2:
        print("Usage: python detect_quality_issues.py <path-to-csv>")
        sys.exit(1)

    df, result = validate_input(sys.argv[1])
    detections = detect_quality_issues(df, result)
    print("\nDetection summary:")
    for d in detections:
        status_icon = "⚠️" if d["status"] == "found" else "✅"
        print(
            f"  {status_icon} {d['check']}: {d['status']} "
            f"({len(d['affected_columns'])} columns)"
        )

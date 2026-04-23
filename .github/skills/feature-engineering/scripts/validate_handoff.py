"""Stage 1 — Validate handoff from Skill A.

Runs the 16 validation checks from DM-001 in contract order.
Generates run ID (DM-003). Loads optional metadata JSON and
transform report when present.

Contract: contracts/validate-handoff.md
"""
from __future__ import annotations

import datetime
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from run_id import generate_run_id
from schemas import SNAKE_CASE_RE


class HandoffValidationError(Exception):
    """Hard-gate failure — pipeline must stop."""


def _find_file(directory: str, pattern: str) -> Optional[str]:
    """Find a file matching a glob pattern in the directory."""
    import glob
    matches = glob.glob(os.path.join(directory, pattern))
    return sorted(matches)[-1] if matches else None


def validate_handoff(
    file_path: str,
    metadata_json_path: Optional[str] = None,
    transformation_report_path: Optional[str] = None,
    search_dir: Optional[str] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Validate the uploaded CSV against Skill A's handoff contract.

    Parameters
    ----------
    file_path : str
        Path to the cleaned CSV.
    metadata_json_path : str, optional
        Path to transform-metadata.json from Skill A.
    transformation_report_path : str, optional
        Path to transform-report.md from Skill A.
    search_dir : str, optional
        Directory to auto-discover metadata/report if paths not given.

    Returns
    -------
    (df, validation_result) — the loaded DataFrame and DM-003 dict.

    Raises
    ------
    HandoffValidationError on any hard-gate failure.
    """
    print("🔍 Validating input against Skill A handoff contract...")

    warnings: List[str] = []

    # --- Check 1: File exists ---
    if not os.path.isfile(file_path):
        raise HandoffValidationError("File not found or not readable.")

    # --- Check 2: Parses as CSV ---
    try:
        df = pd.read_csv(file_path)
    except Exception:
        raise HandoffValidationError(
            "This file is not a valid CSV. Please check the file "
            "format and try again."
        )

    filename = os.path.basename(file_path)

    # --- Check 3: Has columns ---
    if df.shape[1] == 0:
        raise HandoffValidationError("This CSV has no columns.")

    # --- Check 4: Has rows ---
    if df.shape[0] == 0:
        raise HandoffValidationError(
            "This CSV contains headers but no data rows."
        )

    print(f"✅ File: {filename} — valid CSV")
    print(
        f"✅ Shape: {df.shape[0]} rows × {df.shape[1]} columns "
        f"({df.size} cells)"
    )

    # --- Check 5/6: Cell count ---
    cell_count = df.size
    if cell_count > 500_000:
        raise HandoffValidationError(
            f"This dataset exceeds the feature engineering limit "
            f"for Claude.ai ({cell_count} cells). Reduce rows or columns."
        )
    if cell_count > 100_000:
        warnings.append(
            f"This dataset is large ({cell_count} cells). "
            "Feature engineering may be slow."
        )

    # --- Auto-discover metadata/report if search_dir provided ---
    if search_dir and not metadata_json_path:
        metadata_json_path = _find_file(
            search_dir, "*-transform-metadata.json"
        )
    if search_dir and not transformation_report_path:
        transformation_report_path = _find_file(
            search_dir, "*-transform-report.md"
        )

    # --- Load metadata JSON (checks 7, 8, 15) ---
    has_metadata = False
    metadata_provenance_valid = False
    metadata_content: Optional[Dict[str, Any]] = None
    pii_from_metadata: List[Dict[str, Any]] = []

    if metadata_json_path and os.path.isfile(metadata_json_path):
        try:
            with open(metadata_json_path, "r", encoding="utf-8") as f:
                metadata_content = json.load(f)

            # Check 7: Provenance
            produced_by = metadata_content.get("produced_by")
            if produced_by != "skill_a":
                raise HandoffValidationError(
                    "Handoff contract violation: this CSV was not produced "
                    "by Skill A. Please re-run through Skill A first."
                )

            # Check 8: Contract version
            version = metadata_content.get("handoff_contract_version")
            if version != "1.0":
                raise HandoffValidationError(
                    f"Handoff contract violation: unsupported contract "
                    f"version '{version}'. Skill B requires version 1.0."
                )

            has_metadata = True
            metadata_provenance_valid = True

            # Extract PII warnings from metadata
            pii_from_metadata = metadata_content.get("pii_warnings", []) or []

            print("✅ Provenance: produced by Skill A (contract version 1.0)")
        except HandoffValidationError:
            raise
        except Exception as exc:
            warnings.append(
                f"Warning: could not read Skill A metadata. "
                f"Running in fallback mode. ({exc})"
            )

    # --- Load transformation report (check 16) ---
    has_report = False
    report_content: Optional[str] = None
    if transformation_report_path and os.path.isfile(transformation_report_path):
        try:
            with open(transformation_report_path, "r", encoding="utf-8") as f:
                report_content = f.read()
            has_report = True
        except Exception:
            warnings.append(
                "Warning: could not read Skill A transform report. "
                "Proceeding without context."
            )

    # --- Check 9: No duplicate column names ---
    dupes = df.columns[df.columns.duplicated()].tolist()
    if dupes:
        raise HandoffValidationError(
            f"Handoff contract violation: duplicate column names found — "
            f"{dupes}. Skill A should have resolved this. "
            "Please re-run Skill A or fix manually."
        )

    # --- Check 10: Column names snake_case + ASCII ---
    bad_names = [
        str(c) for c in df.columns if not SNAKE_CASE_RE.match(str(c))
    ]
    if bad_names:
        raise HandoffValidationError(
            f"Handoff contract violation: column names not in snake_case — "
            f"{bad_names}. Skill A should have standardized these."
        )

    print("✅ Column names: snake_case, no duplicates")

    # --- Check 11: No all-missing columns ---
    all_missing = [str(c) for c in df.columns if df[c].isna().all()]
    if all_missing:
        raise HandoffValidationError(
            f"Handoff contract violation: column(s) entirely empty — "
            f"{all_missing}. Skill A should have dropped these."
        )

    # --- Check 12: No exact duplicate rows ---
    n_dupes = int(df.duplicated().sum())
    if n_dupes > 0:
        raise HandoffValidationError(
            f"Handoff contract violation: exact duplicate rows found "
            f"({n_dupes} rows). Skill A should have removed these."
        )

    # --- Check 13: Consistent types per column ---
    for col in df.columns:
        if df[col].dtype == object:
            inferred = pd.api.types.infer_dtype(df[col], skipna=True)
            if inferred in ("mixed", "mixed-integer"):
                raise HandoffValidationError(
                    f"Handoff contract violation: column '{col}' has "
                    "mixed types. Skill A should have resolved type "
                    "inconsistencies."
                )

    print("✅ Types: consistent within each column")

    # --- Check 14: Missing values soft check ---
    total_missing = int(df.isna().sum().sum())
    if total_missing > 0 and not has_metadata:
        warnings.append(
            "Some columns have missing values and no Skill A metadata "
            "was found to explain them. Proceeding — but results may "
            "be affected."
        )

    # --- Generate run ID ---
    run_id = generate_run_id("feature")
    print(f"✅ Run ID: {run_id}")

    # --- Metadata/report status ---
    if has_metadata:
        print("ℹ️ Skill A transform metadata: found — provenance verified")
    else:
        print("ℹ️ Skill A transform metadata: not found — fallback mode")

    if has_report:
        print("ℹ️ Skill A transform report: found — context loaded")
    else:
        print("ℹ️ Skill A transform report: not found")

    # --- Build DM-003 ---
    validation_result: Dict[str, Any] = {
        "run_id": run_id,
        "filename": filename,
        "file_path": os.path.abspath(file_path),
        "row_count": int(df.shape[0]),
        "column_count": int(df.shape[1]),
        "cell_count": int(cell_count),
        "column_names": list(str(c) for c in df.columns),
        "column_dtypes": {str(c): str(df[c].dtype) for c in df.columns},
        "has_metadata_json": has_metadata,
        "has_transformation_report": has_report,
        "metadata_provenance_valid": metadata_provenance_valid,
        "metadata_content": metadata_content,
        "report_content": report_content,
        "pii_flags": [],  # populated by scan_pii
        "warnings": warnings,
        "validated_at": datetime.datetime.now().isoformat(),
    }

    # Stash PII from metadata for scan_pii to use
    if pii_from_metadata:
        validation_result["_pii_from_metadata"] = pii_from_metadata

    if warnings:
        for w in warnings:
            print(f"ℹ️ {w}")

    print()
    print("All checks passed. Starting feature engineering pipeline...")
    print()

    return df, validation_result


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python validate_handoff.py <csv_path> [metadata_json] [report_md]")
        sys.exit(1)
    try:
        df, vr = validate_handoff(
            sys.argv[1],
            sys.argv[2] if len(sys.argv) > 2 else None,
            sys.argv[3] if len(sys.argv) > 3 else None,
        )
        print(f"Validation result: {vr['run_id']}")
    except HandoffValidationError as e:
        print(f"❌ {e}")
        sys.exit(1)

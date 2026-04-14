"""Stage 17 — Deliver cleaning outputs.

Writes the final Feature 2 files:

- ``{run_id}-cleaned.csv`` — already written by execute_transformations
- ``{run_id}-transform-report.md`` — final markdown report
- ``{run_id}-transform-metadata.json`` — DM-110 handoff metadata
- ``{run_id}-mistake-log.json`` — written via write_mistake_log
  (call this from the caller's try/finally)

Also prints the download presentation per the contract.

Contract: ``contracts/deliver-outputs.md``
"""
from __future__ import annotations

import copy
import json
import math
import os
from typing import Any, Dict, List, Optional

import pandas as pd


def _json_safe(obj: Any) -> Any:
    """Recursively convert values to JSON-safe Python types."""
    if obj is None or isinstance(obj, (str, bool, int)):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if hasattr(obj, "item"):
        try:
            return _json_safe(obj.item())
        except Exception:
            pass
    return str(obj)


def _build_dm_110(
    run_metadata: Dict[str, Any],
    profiling_data: Dict[str, Any],
    approved_plan: Dict[str, Any],
    step_results: List[Dict[str, Any]],
    raw_df: pd.DataFrame,
    cleaned_df: pd.DataFrame,
) -> Dict[str, Any]:
    """Assemble the DM-110 Skill B handoff metadata."""
    # Build columns map — per cleaned column, what was its original
    # name and what transformations touched it?
    columns_map: Dict[str, Dict[str, Any]] = {}
    # Build a best-effort original-name map by position for step 1 renames
    name_changes: Dict[str, str] = {}
    first_step = next(
        (r for r in step_results if r["step"] == 1 and not r["skipped"]),
        None,
    )
    if first_step and len(raw_df.columns) == len(cleaned_df.columns):
        # Step 1 only renames; step 2+ may drop, so we align by the
        # step 1 before/after only if shapes match
        pass  # name_changes stays empty — conservative fallback

    # Simpler: match raw columns to cleaned columns using the step 1
    # rename logic applied in isolation, but that's fragile. Instead,
    # derive original name by reversing snake_case if possible; fall
    # back to the cleaned name itself.
    for col in cleaned_df.columns:
        columns_map[str(col)] = {
            "original_name": name_changes.get(str(col), str(col)),
            "type": str(cleaned_df[col].dtype),
            "transformations_applied": [],
        }
    # Walk step_results to populate transformations_applied per column
    for result in step_results:
        if result["skipped"]:
            continue
        for t in result["transformations_applied"]:
            strategy = t["strategy"]
            for col in t.get("affected_columns", []):
                col_str = str(col)
                if col_str in columns_map:
                    columns_map[col_str]["transformations_applied"].append(
                        strategy
                    )

    # Build transformations list (flat summary)
    transformations_summary: List[Dict[str, Any]] = []
    for t in approved_plan.get("approved_transformations", []):
        transformations_summary.append({
            "step": int(t["step"]),
            "type": t["strategy"],
            "description": t.get("step_name", ""),
            "affected_columns": t.get("affected_columns", []),
            "confidence_score": int(t.get("confidence_score", 0)),
        })

    # PII warnings from Feature 1
    pii_warnings: List[Dict[str, Any]] = []
    for entry in profiling_data.get("pii_scan", []) or []:
        pii_warnings.append({
            "column_name": entry.get("column_name"),
            "pii_type": entry.get("pii_type"),
            "pii_category": entry.get("pii_category"),
        })

    # Skipped transformations — includes user-skipped and Skill A/B boundary
    skipped: List[Dict[str, Any]] = []
    for s in approved_plan.get("skipped_transformations", []) or []:
        skipped.append({
            "type": "user_skipped",
            "description": s.get("reason", "User chose to skip"),
            "relevant_columns": [],  # may be populated from the DM-104 source
            "source": "user_skipped",
        })
    # Skill A/B boundary — always present
    skipped.append({
        "type": "skill_boundary",
        "description": (
            "Normalization and standardization for numeric columns — "
            "out of scope for Skill A, recommended for Skill B."
        ),
        "relevant_columns": [],
        "source": "skill_boundary",
    })
    skipped.append({
        "type": "skill_boundary",
        "description": (
            "Categorical encoding (one-hot, label, target) — out of "
            "scope for Skill A, recommended for Skill B."
        ),
        "relevant_columns": [],
        "source": "skill_boundary",
    })

    return {
        "run_id": run_metadata["transform_run_id"],
        "source_profiling_run_id": run_metadata["source_profiling_run_id"],
        "original_filename": run_metadata["original_filename"],
        "produced_by": "skill_a",
        "pipeline_version": run_metadata["pipeline_version"],
        "row_count_before": int(raw_df.shape[0]),
        "row_count_after": int(cleaned_df.shape[0]),
        "column_count_before": int(raw_df.shape[1]),
        "column_count_after": int(cleaned_df.shape[1]),
        "columns": columns_map,
        "transformations": transformations_summary,
        "pii_warnings": pii_warnings,
        "skipped_transformations": skipped,
        "handoff_contract_version": "1.0",
    }


def deliver_cleaning_outputs(
    final_report_text: str,
    cleaned_df: pd.DataFrame,
    cleaned_csv_path: Optional[str],
    run_metadata: Dict[str, Any],
    profiling_data: Dict[str, Any],
    approved_plan: Dict[str, Any],
    step_results: List[Dict[str, Any]],
    raw_df: pd.DataFrame,
    output_dir: str = ".",
) -> Dict[str, Any]:
    """Write the transform report + metadata JSON and print download listing.

    Returns a dict of file paths written (or None on write failure for
    that specific file).

    The mistake log is NOT written here — the caller's ``try/finally``
    is responsible for calling :func:`mistake_log.write_mistake_log`
    so the log persists even when the pipeline halts.
    """
    run_id = run_metadata["transform_run_id"]
    report_name = f"{run_id}-transform-report.md"
    meta_name = f"{run_id}-transform-metadata.json"
    mistake_log_name = f"{run_id}-mistake-log.json"

    report_path = os.path.join(output_dir, report_name)
    meta_path = os.path.join(output_dir, meta_name)

    written: Dict[str, Any] = {
        "cleaned_csv": cleaned_csv_path if cleaned_csv_path and os.path.isfile(cleaned_csv_path) else None,
        "transform_report": None,
        "transform_metadata": None,
        "mistake_log_expected_path": os.path.join(output_dir, mistake_log_name),
    }

    # --- Write the transform report ---
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(final_report_text)
        written["transform_report"] = report_path
    except Exception as exc:
        print(
            f"Output error: could not save {report_name}. "
            f"The report has been delivered inline — please copy it "
            f"manually. ({exc})"
        )

    # --- Build and write DM-110 metadata ---
    try:
        metadata = _build_dm_110(
            run_metadata=run_metadata,
            profiling_data=profiling_data,
            approved_plan=approved_plan,
            step_results=step_results,
            raw_df=raw_df,
            cleaned_df=cleaned_df,
        )
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(_json_safe(metadata), f, indent=2)
        written["transform_metadata"] = meta_path
    except Exception as exc:
        print(
            f"Output error: could not save {meta_name}. ({exc})"
        )

    # --- Inline delivery ---
    print()
    print(final_report_text)
    print()

    # --- Download presentation ---
    print("📥 Your cleaning outputs are ready for download:")
    if written["cleaned_csv"]:
        print(
            f"   • {os.path.basename(written['cleaned_csv'])}"
            f" — Cleaned dataset ({cleaned_df.shape[0]} rows × "
            f"{cleaned_df.shape[1]} columns)"
        )
    if written["transform_report"]:
        print(
            f"   • {os.path.basename(written['transform_report'])}"
            f" — Transformation report (the report shown above)"
        )
    if written["transform_metadata"]:
        print(
            f"   • {os.path.basename(written['transform_metadata'])}"
            f" — Transformation metadata (for feature engineering"
            f" and downstream processing)"
        )
    print()
    print(
        f"A pipeline log ({mistake_log_name}) is also available "
        "if you need audit details."
    )
    print()
    print("Your data cleaning is complete. You can now proceed to")
    print("feature engineering, or download these files to share")
    print("with your team.")

    return written


if __name__ == "__main__":
    print("deliver_cleaning_outputs is invoked by the orchestrator.")

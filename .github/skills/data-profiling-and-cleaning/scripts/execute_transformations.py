"""Stage 13 — Execute approved transformations.

Orchestrator for the 7 cleaning steps. Per DM-107 and the
execute-transformations contract:

- Captures before/after metrics for every step (via
  :func:`metrics.capture_metrics`)
- Runs the DM-108 high-impact checks after each step
- Validates required parameters before dispatching (via
  :func:`catalog.validate_transformation_parameters`)
- Logs execution errors and high-impact flags to the mistake log
- Writes the cleaned CSV to ``{transform_run_id}-cleaned.csv``
- Halts immediately on any step error — caller wraps in try/finally
  so the mistake log persists

Contract: ``contracts/execute-transformations.md``
"""
from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Tuple

import numpy as np
import pandas as pd

from catalog import (
    TRANSFORMATION_CATALOG,
    get_step_name,
    validate_transformation_parameters,
)
from high_impact import check_high_impact
from metrics import capture_metrics
from mistake_log import log_entry
from step_1_column_names import step_1_column_names
from step_2_drop_missing import step_2_drop_missing
from step_3_type_coercion import step_3_type_coercion
from step_4_invalid_categories import step_4_invalid_categories
from step_5_imputation import step_5_imputation
from step_6_deduplication import step_6_deduplication
from step_7_outliers import step_7_outliers


# Step number → step function
STEP_FUNCTIONS: Dict[int, Callable] = {
    1: step_1_column_names,
    2: step_2_drop_missing,
    3: step_3_type_coercion,
    4: step_4_invalid_categories,
    5: step_5_imputation,
    6: step_6_deduplication,
    7: step_7_outliers,
}


class ExecutionError(Exception):
    """Raised when a step function fails."""


def _partition_by_step(
    approved_transformations: List[Dict[str, Any]],
) -> Dict[int, List[Dict[str, Any]]]:
    """Group approved transformations by step number."""
    by_step: Dict[int, List[Dict[str, Any]]] = {s: [] for s in range(1, 8)}
    for t in approved_transformations:
        step = int(t["step"])
        if 1 <= step <= 7:
            by_step[step].append(t)
    return by_step


def _validate_parameters(
    transformations: List[Dict[str, Any]],
    step: int,
) -> None:
    """Validate required parameters for all transformations in a step.

    Raises ExecutionError on the first missing parameter.
    """
    for t in transformations:
        missing = validate_transformation_parameters(
            t["strategy"], t.get("parameters", {})
        )
        if missing:
            raise ExecutionError(
                f"Pipeline error: missing required parameter "
                f"'{missing[0]}' for strategy '{t['strategy']}' "
                f"in step {step}."
            )


def _get_affected_columns(
    transformations: List[Dict[str, Any]],
) -> List[str]:
    """Collect the union of affected_columns across transformations."""
    cols: set[str] = set()
    for t in transformations:
        for c in t.get("affected_columns", []) or []:
            cols.add(str(c))
    return sorted(cols)


def _summarise_step(
    step: int,
    step_name: str,
    metrics_before: Dict[str, Any],
    metrics_after: Dict[str, Any],
) -> str:
    """Produce a one-line human summary of what changed."""
    ds_b = metrics_before["dataset"]
    ds_a = metrics_after["dataset"]
    delta_rows = ds_a["n_rows"] - ds_b["n_rows"]
    delta_cols = ds_a["n_columns"] - ds_b["n_columns"]
    parts: List[str] = []
    if delta_rows != 0:
        parts.append(f"{abs(delta_rows)} row(s) {'removed' if delta_rows < 0 else 'added'}")
    if delta_cols != 0:
        parts.append(f"{abs(delta_cols)} column(s) {'removed' if delta_cols < 0 else 'added'}")
    missing_delta = ds_a["n_missing_cells"] - ds_b["n_missing_cells"]
    if missing_delta != 0:
        parts.append(
            f"{abs(missing_delta)} missing cell(s) "
            f"{'filled' if missing_delta < 0 else 'introduced'}"
        )
    if not parts:
        parts.append("no structural changes")
    return f"{step_name}: " + ", ".join(parts)


def execute_transformations(
    raw_df: pd.DataFrame,
    approved_plan: Dict[str, Any],
    run_metadata: Dict[str, Any],
    mistake_log: Dict[str, Any],
    output_dir: str = ".",
) -> Tuple[pd.DataFrame, List[Dict[str, Any]], str]:
    """Execute the approved plan and return (cleaned_df, step_results, csv_path).

    Parameters
    ----------
    raw_df:
        The original raw DataFrame loaded in stage 10.
    approved_plan:
        DM-106 approved plan (with approved/rejected/skipped/dep warnings).
    run_metadata:
        DM-102 run metadata.
    mistake_log:
        DM-112 in-memory log. Entries appended for errors and high-impact flags.
    output_dir:
        Where to write the cleaned CSV.

    Returns
    -------
    (cleaned_df, step_results, cleaned_csv_path)
    """
    print("⚙️ Executing approved transformations...\n")

    # Build the RNG once — per DM-102 the seed is 42
    rng = np.random.default_rng(run_metadata["random_seed"])

    approved = approved_plan.get("approved_transformations", [])
    dep_warnings = approved_plan.get("dependency_warnings", [])

    # Surface any dependency warnings upfront (DM-106)
    for w in dep_warnings:
        print(f"   ⚠️ {w['warning']}")
        log_entry(
            mistake_log, "edge_case_warning",
            step=int(w.get("skipped_step", 0)),
            transformation_type="dependency_warning",
            description=w["warning"],
            resolution="Proceeding with caution; flagged in report",
        )

    by_step = _partition_by_step(approved)

    current_df = raw_df
    step_results: List[Dict[str, Any]] = []

    for step in range(1, 8):
        step_name = get_step_name(step)
        transformations = by_step[step]

        if not transformations:
            # Record a skipped step in DM-107
            step_results.append({
                "step": step,
                "step_name": step_name,
                "transformations_applied": [],
                "metrics_before": capture_metrics(current_df),
                "metrics_after": capture_metrics(current_df),
                "high_impact_flags": [],
                "skipped": True,
            })
            continue

        # Validate parameters before touching data
        try:
            _validate_parameters(transformations, step)
        except ExecutionError as e:
            log_entry(
                mistake_log, "execution_error", step=step,
                transformation_type=step_name,
                description=str(e),
                resolution="Pipeline halted",
            )
            raise

        affected_columns = _get_affected_columns(transformations)

        # Metrics before
        metrics_before = capture_metrics(current_df, affected_columns)

        # Dispatch
        fn = STEP_FUNCTIONS[step]
        try:
            current_df = fn(current_df, transformations, rng)
        except Exception as exc:
            message = (
                f"Transformation failed at step {step} ({step_name}): "
                f"{exc}. Please try again in a new session."
            )
            log_entry(
                mistake_log, "execution_error", step=step,
                transformation_type=step_name,
                description=message,
                resolution="Pipeline halted",
                affected_columns=affected_columns,
            )
            print(f"❌ {message}")
            raise ExecutionError(message) from exc

        # Guard: if the DataFrame is empty, halt
        if current_df.empty or current_df.shape[1] == 0:
            message = (
                "Pipeline error: all rows were removed during transformation. "
                "Please review the approved plan."
            )
            log_entry(
                mistake_log, "execution_error", step=step,
                transformation_type=step_name,
                description=message,
                resolution="Pipeline halted",
            )
            print(f"❌ {message}")
            raise ExecutionError(message)

        # Metrics after — need to recompute affected_columns because
        # step 1 may have renamed them
        if step == 1:
            # Post-rename, use every column that exists now
            metrics_after = capture_metrics(current_df)
        else:
            metrics_after = capture_metrics(current_df, affected_columns)

        # High-impact flags — compute once per transformation, reuse
        # for both the mistake log and the step result
        all_flags: List[Dict[str, Any]] = []
        for t in transformations:
            all_flags.extend(check_high_impact(
                step=step, step_name=step_name,
                strategy=t["strategy"],
                metrics_before=metrics_before,
                metrics_after=metrics_after,
                affected_columns=t.get("affected_columns", []) or [],
            ))
        for flag in all_flags:
            log_entry(
                mistake_log, "high_impact_flag", step=step,
                transformation_type=step_name,
                description=flag["message"],
                resolution=(
                    "Proceeding; flag surfaced in transformation report"
                ),
                affected_columns=flag.get("affected_columns", []),
            )

        step_result: Dict[str, Any] = {
            "step": step,
            "step_name": step_name,
            "transformations_applied": [
                {
                    "id": t.get("id"),
                    "strategy": t["strategy"],
                    "affected_columns": t.get("affected_columns", []),
                    "parameters": t.get("parameters", {}),
                }
                for t in transformations
            ],
            "metrics_before": metrics_before,
            "metrics_after": metrics_after,
            "high_impact_flags": all_flags,
            "skipped": False,
        }
        step_results.append(step_result)

        summary = _summarise_step(
            step, step_name, metrics_before, metrics_after
        )
        print(f"Step {step}: {summary} ✅")
        for flag in all_flags:
            print(f"   ⚠️ {flag['condition']}: {flag['message']}")

    # Write the cleaned CSV
    run_id = run_metadata["transform_run_id"]
    csv_path = os.path.join(output_dir, f"{run_id}-cleaned.csv")
    try:
        current_df.to_csv(csv_path, index=False)
    except Exception as exc:
        log_entry(
            mistake_log, "execution_error", step=0,
            transformation_type="output_write",
            description=f"Failed to write cleaned CSV: {exc}",
            resolution="Pipeline halted",
        )
        raise ExecutionError(
            f"Pipeline error: could not write cleaned CSV to {csv_path}"
        ) from exc

    print("\nExecution complete. Running verification...\n")
    return current_df, step_results, csv_path


if __name__ == "__main__":
    # Quick smoke test with an inline plan
    df = pd.DataFrame({
        "Sales $": [100, 200, 300, 100, 200],
        "Notes": [None, None, None, None, None],
        "Price": ["$1,000", "$2,000", "$3,000", "$1,000", "$2,000"],
    })
    plan = {
        "approved_transformations": [
            {"id": "t-1-01", "step": 1, "step_name": "column_name_standardization",
             "strategy": "standardize_to_snake_case",
             "affected_columns": list(df.columns), "parameters": {},
             "is_custom": False, "confidence_score": 95,
             "confidence_band": "High", "review_round": 1},
            {"id": "t-2-01", "step": 2, "step_name": "drop_all_missing_columns",
             "strategy": "drop_column", "affected_columns": ["notes"],
             "parameters": {}, "is_custom": False,
             "confidence_score": 95, "confidence_band": "High",
             "review_round": 1},
            {"id": "t-3-01", "step": 3, "step_name": "type_coercion",
             "strategy": "parse_currency_strip_symbols",
             "affected_columns": ["price"], "parameters": {},
             "is_custom": False, "confidence_score": 95,
             "confidence_band": "High", "review_round": 1},
            {"id": "t-6-01", "step": 6, "step_name": "deduplication",
             "strategy": "drop_exact_keep_first", "affected_columns": [],
             "parameters": {}, "is_custom": False,
             "confidence_score": 95, "confidence_band": "High",
             "review_round": 1},
        ],
        "rejected_transformations": [],
        "skipped_transformations": [],
        "human_review_decisions": [],
        "dependency_warnings": [],
    }
    run_metadata = {
        "transform_run_id": "transform-20260414-test-0000",
        "source_profiling_run_id": "profile-20260414-test-0000",
        "original_filename": "test.csv",
        "original_file_path": "/tmp/test.csv",
        "started_at": "2026-04-14T00:00:00",
        "random_seed": 42,
        "pipeline_version": "1.0",
    }
    from mistake_log import build_mistake_log
    log = build_mistake_log(run_metadata["transform_run_id"])
    cleaned, results, path = execute_transformations(
        df, plan, run_metadata, log, output_dir="/tmp",
    )
    print(f"\nResult shape: {cleaned.shape}")
    print(f"Columns: {list(cleaned.columns)}")
    print(f"Written to: {path}")
    print(f"Mistake log entries: {len(log['entries'])}")
    os.remove(path)

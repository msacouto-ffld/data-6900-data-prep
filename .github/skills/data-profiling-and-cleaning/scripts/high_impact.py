"""Detect high-impact transformation conditions.

Runs after each step function and compares before/after metrics
against the DM-108 thresholds. Flags are collected into
DM-107's ``high_impact_flags`` field and surfaced in the
transformation report.

See :mod:`thresholds` for the canonical threshold dict.
"""
from __future__ import annotations

from typing import Any, Dict, List

from thresholds import HIGH_IMPACT_THRESHOLDS


def _pct(before: float, after: float) -> float:
    """Percentage change from before to after (0 if before == 0)."""
    if before == 0:
        return 0.0
    return ((before - after) / before) * 100.0


def check_high_impact(
    step: int,
    step_name: str,
    strategy: str,
    metrics_before: Dict[str, Any],
    metrics_after: Dict[str, Any],
    affected_columns: List[str],
) -> List[Dict[str, Any]]:
    """Return a list of high-impact flags for this step.

    Each flag is a DM-107 entry with ``type: "high_impact_flag"``,
    a ``condition`` name, actual ``value``, triggering ``threshold``,
    human-readable ``message``, and ``affected_columns``.

    Parameters
    ----------
    step:
        Step number (1–7).
    step_name:
        Canonical step name from the catalog.
    strategy:
        The strategy that was executed (used for context in the
        message).
    metrics_before, metrics_after:
        DM-107 metric dicts from :func:`metrics.capture_metrics`.
    affected_columns:
        Columns the strategy targeted.
    """
    flags: List[Dict[str, Any]] = []

    ds_before = metrics_before.get("dataset", {})
    ds_after = metrics_after.get("dataset", {})
    cols_before = metrics_before.get("columns", {})
    cols_after = metrics_after.get("columns", {})

    rows_before = ds_before.get("n_rows", 0)
    rows_after = ds_after.get("n_rows", 0)
    cols_count_before = ds_before.get("n_columns", 0)
    cols_count_after = ds_after.get("n_columns", 0)

    # ----- Row reduction -----
    if rows_before > 0 and rows_after < rows_before:
        reduction_pct = _pct(rows_before, rows_after)
        threshold = HIGH_IMPACT_THRESHOLDS["row_reduction_pct"]
        if reduction_pct > threshold:
            flags.append({
                "type": "high_impact_flag",
                "condition": "row_reduction",
                "value": round(reduction_pct, 2),
                "threshold": threshold,
                "message": (
                    f"Step {step} ({step_name}, strategy {strategy}) "
                    f"removed {reduction_pct:.1f}% of rows "
                    f"({rows_before} → {rows_after}), which exceeds the "
                    f"{threshold}% threshold."
                ),
                "affected_columns": list(affected_columns),
            })

    # ----- Column dropped -----
    if cols_count_after < cols_count_before:
        n_dropped = cols_count_before - cols_count_after
        if HIGH_IMPACT_THRESHOLDS["column_dropped"]:
            flags.append({
                "type": "high_impact_flag",
                "condition": "column_dropped",
                "value": float(n_dropped),
                "threshold": 1.0,
                "message": (
                    f"Step {step} ({step_name}) dropped {n_dropped} "
                    "column(s). Column drops are always high-impact "
                    "because they change the dataset's schema."
                ),
                "affected_columns": list(affected_columns),
            })

    # ----- Per-column imputation percentage (step 5) -----
    if step == 5:
        imp_threshold = HIGH_IMPACT_THRESHOLDS["imputation_pct"]
        for col in affected_columns:
            before_col = cols_before.get(col, {})
            after_col = cols_after.get(col, {})
            if not before_col or not after_col:
                continue
            n_before_missing = before_col.get("n_missing", 0)
            n_total = before_col.get("n_total", 0)
            if n_total > 0:
                imputed_pct = (n_before_missing / n_total) * 100.0
                if imputed_pct > imp_threshold:
                    flags.append({
                        "type": "high_impact_flag",
                        "condition": "imputation_pct",
                        "value": round(imputed_pct, 2),
                        "threshold": imp_threshold,
                        "message": (
                            f"Step 5 imputed {imputed_pct:.1f}% of values "
                            f"in column '{col}' ({n_before_missing}/{n_total}), "
                            f"exceeding the {imp_threshold}% threshold. "
                            "Heavy imputation may distort the column's "
                            "statistical properties."
                        ),
                        "affected_columns": [col],
                    })

    # ----- Per-column outlier treatment percentage (step 7) -----
    if step == 7:
        out_threshold = HIGH_IMPACT_THRESHOLDS["outlier_treatment_pct"]
        for col in affected_columns:
            before_col = cols_before.get(col, {})
            after_col = cols_after.get(col, {})
            if not before_col or not after_col:
                continue
            # Approximate outlier treatment count via mean shift /
            # row removal — here we just flag if the mean shifted a lot
            # (handled by mean_shift_pct below) OR if rows were removed.
            before_n = before_col.get("n_total", 0)
            after_n = after_col.get("n_total", 0)
            if before_n > 0 and after_n < before_n:
                treated_pct = ((before_n - after_n) / before_n) * 100.0
                if treated_pct > out_threshold:
                    flags.append({
                        "type": "high_impact_flag",
                        "condition": "outlier_treatment_pct",
                        "value": round(treated_pct, 2),
                        "threshold": out_threshold,
                        "message": (
                            f"Step 7 removed or capped {treated_pct:.1f}% "
                            f"of values in column '{col}', exceeding the "
                            f"{out_threshold}% threshold."
                        ),
                        "affected_columns": [col],
                    })

    # ----- Per-column mean shift (any step with numeric columns) -----
    mean_threshold = HIGH_IMPACT_THRESHOLDS["mean_shift_pct"]
    for col in affected_columns:
        before_col = cols_before.get(col, {})
        after_col = cols_after.get(col, {})
        before_mean = before_col.get("mean")
        after_mean = after_col.get("mean")
        if before_mean is None or after_mean is None:
            continue
        if before_mean == 0:
            continue
        shift_pct = abs((after_mean - before_mean) / before_mean) * 100.0
        if shift_pct > mean_threshold:
            flags.append({
                "type": "high_impact_flag",
                "condition": "mean_shift",
                "value": round(shift_pct, 2),
                "threshold": mean_threshold,
                "message": (
                    f"Column '{col}' mean shifted by {shift_pct:.1f}% "
                    f"({before_mean:.2f} → {after_mean:.2f}) after "
                    f"step {step}, exceeding the {mean_threshold}% threshold. "
                    "Large mean shifts suggest the transformation changed "
                    "the column's statistical profile materially."
                ),
                "affected_columns": [col],
            })

    return flags


if __name__ == "__main__":
    # Smoke test
    before = {
        "dataset": {"n_rows": 100, "n_columns": 5},
        "columns": {"a": {"mean": 100.0, "n_missing": 40, "n_total": 100}},
    }
    after = {
        "dataset": {"n_rows": 80, "n_columns": 4},
        "columns": {"a": {"mean": 150.0, "n_missing": 0, "n_total": 80}},
    }
    flags = check_high_impact(
        step=5, step_name="missing_value_imputation",
        strategy="impute_mean",
        metrics_before=before, metrics_after=after,
        affected_columns=["a"],
    )
    print(f"Flags raised: {len(flags)}")
    for f in flags:
        print(f"  - {f['condition']}: {f['message']}")

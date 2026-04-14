"""Before/after metric capture for step execution.

Every step function calls :func:`capture_metrics` twice (before and
after its transformation). The result populates DM-107's
``metrics_before`` and ``metrics_after`` fields, which feed the
report generator and the Data Analyst verifier.

Per DM-107: dataset-level metrics are captured for every step;
column-level metrics are captured only for ``affected_columns`` plus
any columns that triggered high-impact flags. This keeps the data
structure manageable for wide datasets.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

import pandas as pd


def _column_metrics(series: pd.Series) -> Dict[str, Any]:
    """Compute a single column's metric dict."""
    n_total = len(series)
    n_missing = int(series.isna().sum())
    n_unique = int(series.nunique(dropna=True))
    dtype = str(series.dtype)

    entry: Dict[str, Any] = {
        "dtype": dtype,
        "n_total": n_total,
        "n_missing": n_missing,
        "pct_missing": round(n_missing / n_total * 100, 2)
        if n_total else 0.0,
        "n_unique": n_unique,
    }

    # Numeric summary statistics — only for numeric dtypes
    if pd.api.types.is_numeric_dtype(series):
        non_null = series.dropna()
        if len(non_null) > 0:
            entry["mean"] = float(non_null.mean())
            entry["std"] = float(non_null.std()) if len(non_null) > 1 else 0.0
            entry["min"] = float(non_null.min())
            entry["max"] = float(non_null.max())
            entry["median"] = float(non_null.median())
        else:
            entry["mean"] = None
            entry["std"] = None
            entry["min"] = None
            entry["max"] = None
            entry["median"] = None

    return entry


def capture_metrics(
    df: pd.DataFrame,
    affected_columns: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """Capture dataset-level + per-affected-column metrics.

    Parameters
    ----------
    df:
        DataFrame at the current state.
    affected_columns:
        Optional iterable of column names to capture column-level
        metrics for. If ``None`` or empty, only dataset-level metrics
        are returned. Column names not present in ``df`` are silently
        ignored (they may have been dropped by the step).

    Returns
    -------
    dict
        ``{"dataset": {...}, "columns": {col: {...}, ...}}``
    """
    affected = list(affected_columns or [])

    total_cells = df.size if df.size > 0 else 0
    total_missing = int(df.isna().sum().sum())
    total_duplicates = int(df.duplicated().sum())

    dataset_metrics: Dict[str, Any] = {
        "n_rows": int(df.shape[0]),
        "n_columns": int(df.shape[1]),
        "n_cells": int(total_cells),
        "n_missing_cells": total_missing,
        "pct_missing_cells": round(total_missing / total_cells * 100, 2)
        if total_cells else 0.0,
        "n_duplicate_rows": total_duplicates,
        "pct_duplicate_rows": round(total_duplicates / df.shape[0] * 100, 2)
        if df.shape[0] else 0.0,
    }

    column_metrics: Dict[str, Dict[str, Any]] = {}
    for col in affected:
        if col in df.columns:
            column_metrics[col] = _column_metrics(df[col])

    return {"dataset": dataset_metrics, "columns": column_metrics}


if __name__ == "__main__":
    # Smoke test
    import numpy as np
    df = pd.DataFrame({
        "a": [1, 2, 3, 4, None],
        "b": ["x", "y", None, "x", "y"],
        "c": [1, 1, 1, 1, 1],
    })
    # Add a duplicate row
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    metrics = capture_metrics(df, affected_columns=["a", "b"])
    print("Dataset metrics:")
    for k, v in metrics["dataset"].items():
        print(f"  {k}: {v}")
    print("\nColumn metrics for 'a':")
    for k, v in metrics["columns"]["a"].items():
        print(f"  {k}: {v}")

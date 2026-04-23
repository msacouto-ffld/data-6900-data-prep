"""Stage 3 — Generate dataset summary (DM-004).

Produces the structured dict that every LLM call receives. The LLM
never sees the raw CSV — only this summary.

Contract: contracts/generate-dataset-summary.md
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import pandas as pd


def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


def generate_dataset_summary(
    df: pd.DataFrame,
    validation_result: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the DM-004 dataset summary.

    PII-flagged columns get ``sample_values: ["[PII — values hidden]"]``.
    """
    pii_cols = {
        f["column_name"] for f in validation_result.get("pii_flags", [])
    }

    columns: List[Dict[str, Any]] = []
    for col in df.columns:
        col_str = str(col)
        series = df[col]
        n_missing = int(series.isna().sum())
        n_total = len(series)
        n_unique = int(series.nunique(dropna=True))
        is_unique = n_unique == n_total

        # Sample values
        if col_str in pii_cols:
            sample_values = ["[PII — values hidden]"]
        else:
            non_null = series.dropna().head(5)
            sample_values = [
                v if not isinstance(v, float) or not math.isnan(v) else None
                for v in non_null.tolist()
            ]

        # Stats (numeric only)
        stats: Dict[str, Optional[float]] = {
            "mean": None, "std": None, "min": None, "max": None, "median": None,
        }
        if pd.api.types.is_numeric_dtype(series):
            nn = series.dropna()
            if len(nn) > 0:
                stats["mean"] = _safe_float(nn.mean())
                stats["std"] = _safe_float(nn.std()) if len(nn) > 1 else 0.0
                stats["min"] = _safe_float(nn.min())
                stats["max"] = _safe_float(nn.max())
                stats["median"] = _safe_float(nn.median())

        pii_flag = None
        for f in validation_result.get("pii_flags", []):
            if f["column_name"] == col_str:
                pii_flag = f["pii_type"]
                break

        columns.append({
            "name": col_str,
            "dtype": str(series.dtype),
            "n_missing": n_missing,
            "pct_missing": round(n_missing / n_total * 100, 2) if n_total else 0.0,
            "n_unique": n_unique,
            "is_unique": is_unique,
            "sample_values": sample_values,
            "stats": stats,
            "pii_flag": pii_flag,
        })

    summary: Dict[str, Any] = {
        "run_id": validation_result["run_id"],
        "filename": validation_result["filename"],
        "row_count": int(df.shape[0]),
        "column_count": int(df.shape[1]),
        "columns": columns,
        "skill_a_metadata": validation_result.get("metadata_content"),
        "skill_a_context": validation_result.get("report_content"),
    }

    return summary


if __name__ == "__main__":
    import numpy as np
    df = pd.DataFrame({
        "sale_amount": [100.0, 200.0, np.nan, 400.0],
        "category": ["A", "B", "A", "C"],
        "email": ["a@x.com", "b@x.com", "c@x.com", "d@x.com"],
    })
    vr = {
        "run_id": "feature-test",
        "filename": "test.csv",
        "pii_flags": [
            {"column_name": "email", "pii_type": "direct_contact"},
        ],
    }
    summary = generate_dataset_summary(df, vr)
    for col in summary["columns"]:
        print(f"  {col['name']}: dtype={col['dtype']}, "
              f"missing={col['n_missing']}, samples={col['sample_values']}")

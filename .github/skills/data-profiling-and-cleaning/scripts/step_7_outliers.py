"""Step 7 — Outlier treatment.

Strategies:

- ``cap_at_percentile`` — clip values outside [p_lower, p_upper] percentiles
- ``remove_rows`` — drop rows whose values fall outside the bounds
- ``flag_only`` — log only
- ``winsorize`` — same as cap_at_percentile (alias)
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd


STRATEGIES = {
    "cap_at_percentile",
    "remove_rows",
    "flag_only",
    "winsorize",
}


def _compute_bounds(
    series: pd.Series,
    p_lower: float,
    p_upper: float,
) -> tuple[float, float]:
    """Return (lower_bound, upper_bound) at the given percentiles."""
    non_null = series.dropna()
    if len(non_null) == 0:
        return float("-inf"), float("inf")
    return (
        float(non_null.quantile(p_lower / 100.0)),
        float(non_null.quantile(p_upper / 100.0)),
    )


def step_7_outliers(
    df: pd.DataFrame,
    transformations: List[Dict[str, Any]],
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Apply approved outlier treatments."""
    if not transformations:
        return df

    result = df.copy()
    rows_to_drop: set[int] = set()

    for t in transformations:
        strategy = t["strategy"]
        if strategy not in STRATEGIES:
            raise ValueError(
                f"step_7: unknown strategy {strategy!r}. "
                f"Known strategies: {sorted(STRATEGIES)}"
            )
        params = t.get("parameters", {})

        if strategy == "flag_only":
            continue

        p_lower = params.get("percentile_lower")
        p_upper = params.get("percentile_upper")
        if p_lower is None or p_upper is None:
            raise ValueError(
                f"step_7: {strategy} requires percentile_lower and "
                f"percentile_upper parameters"
            )

        for col in t.get("affected_columns", []):
            if col not in result.columns:
                continue
            if not pd.api.types.is_numeric_dtype(result[col]):
                # Skip non-numeric columns — outlier treatment
                # only applies to numeric data
                continue

            low, high = _compute_bounds(result[col], p_lower, p_upper)

            if strategy in ("cap_at_percentile", "winsorize"):
                result[col] = result[col].clip(lower=low, upper=high)
            elif strategy == "remove_rows":
                mask = (result[col] >= low) & (result[col] <= high)
                # NaN survives — clip outlier detection cannot remove
                # rows based on missing values
                mask = mask | result[col].isna()
                out_of_bounds = result.index[~mask]
                rows_to_drop.update(out_of_bounds.tolist())

    if rows_to_drop:
        result = result.drop(index=list(rows_to_drop))
        result = result.reset_index(drop=True)

    return result


if __name__ == "__main__":
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "value": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1000],  # 1000 is outlier
    })
    print(f"Before: min={df.value.min()}, max={df.value.max()}")

    # Cap at 5th and 95th percentile
    out = step_7_outliers(df, [
        {"strategy": "cap_at_percentile", "affected_columns": ["value"],
         "parameters": {"percentile_lower": 5, "percentile_upper": 95}},
    ], rng)
    print(f"After cap: min={out.value.min()}, max={out.value.max()}")
    assert out.value.max() < 1000

    # Remove rows instead
    out2 = step_7_outliers(df, [
        {"strategy": "remove_rows", "affected_columns": ["value"],
         "parameters": {"percentile_lower": 5, "percentile_upper": 95}},
    ], rng)
    print(f"After remove: {len(out2)} rows (from {len(df)})")

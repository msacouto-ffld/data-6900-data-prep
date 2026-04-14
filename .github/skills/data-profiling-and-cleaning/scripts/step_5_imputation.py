"""Step 5 — Missing value imputation.

Strategies:

- ``drop_rows`` — drop rows where any affected column is missing
- ``drop_column`` — drop the column entirely
- ``impute_mean`` / ``impute_median`` / ``impute_mode`` — scikit-learn
  ``SimpleImputer``
- ``impute_constant`` — fill with explicit ``fill_value``
- ``impute_most_frequent`` — alias for mode
- ``impute_unknown`` — fill with "Unknown" (or custom fill_value)

Determinism: scikit-learn ``SimpleImputer`` is deterministic for all
strategies used here; no random_state parameter needed. The pipeline's
overall determinism contract (random_seed=42) is honored by the step
not introducing any stochastic operations.
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

try:
    from sklearn.impute import SimpleImputer
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


STRATEGIES = {
    "drop_rows",
    "drop_column",
    "impute_mean",
    "impute_median",
    "impute_mode",
    "impute_constant",
    "impute_most_frequent",
    "impute_unknown",
}


def _sklearn_impute(
    df: pd.DataFrame,
    col: str,
    sklearn_strategy: str,
    fill_value: Any = None,
) -> pd.DataFrame:
    """Apply a scikit-learn SimpleImputer to a single column."""
    if not SKLEARN_AVAILABLE:
        # Pandas fallback
        return _pandas_impute_fallback(df, col, sklearn_strategy, fill_value)

    kwargs: Dict[str, Any] = {"strategy": sklearn_strategy}
    if sklearn_strategy == "constant":
        kwargs["fill_value"] = fill_value

    imputer = SimpleImputer(**kwargs)
    series = df[col]
    # SimpleImputer needs 2D input
    reshaped = series.to_numpy().reshape(-1, 1)
    try:
        imputed = imputer.fit_transform(reshaped).ravel()
    except Exception:
        # Fall back to pandas on failures (e.g. all-NaN numeric column)
        return _pandas_impute_fallback(df, col, sklearn_strategy, fill_value)

    result = df.copy()
    result[col] = imputed
    # Restore dtype where possible
    try:
        result[col] = result[col].astype(df[col].dtype)
    except (TypeError, ValueError):
        pass
    return result


def _pandas_impute_fallback(
    df: pd.DataFrame,
    col: str,
    sklearn_strategy: str,
    fill_value: Any,
) -> pd.DataFrame:
    """Fallback imputation when sklearn is unavailable or errors out."""
    result = df.copy()
    series = result[col]
    if sklearn_strategy == "mean":
        value = series.mean()
    elif sklearn_strategy == "median":
        value = series.median()
    elif sklearn_strategy in ("most_frequent", "mode"):
        modes = series.mode(dropna=True)
        value = modes.iloc[0] if len(modes) > 0 else fill_value
    elif sklearn_strategy == "constant":
        value = fill_value
    else:
        return result
    result[col] = series.fillna(value)
    return result


def step_5_imputation(
    df: pd.DataFrame,
    transformations: List[Dict[str, Any]],
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Apply approved imputation transformations.

    Order: drop_column → drop_rows → per-column imputation. Dropping
    comes first so we don't waste work imputing values in a column
    that's about to be dropped.
    """
    if not transformations:
        return df

    # Partition transformations by strategy group
    drop_col_cols: List[str] = []
    drop_row_cols: List[str] = []
    impute_ops: List[Dict[str, Any]] = []

    for t in transformations:
        strategy = t["strategy"]
        if strategy not in STRATEGIES:
            raise ValueError(
                f"step_5: unknown strategy {strategy!r}. "
                f"Known strategies: {sorted(STRATEGIES)}"
            )
        if strategy == "drop_column":
            drop_col_cols.extend(t.get("affected_columns", []))
        elif strategy == "drop_rows":
            drop_row_cols.extend(t.get("affected_columns", []))
        else:
            impute_ops.append(t)

    result = df.copy()

    # 1. Drop columns
    drop_col_cols = [c for c in drop_col_cols if c in result.columns]
    if drop_col_cols:
        result = result.drop(columns=drop_col_cols)

    # 2. Drop rows where any affected column is NaN
    drop_row_cols = [c for c in drop_row_cols if c in result.columns]
    if drop_row_cols:
        result = result.dropna(subset=drop_row_cols)

    # 3. Per-column imputation
    for t in impute_ops:
        strategy = t["strategy"]
        params = t.get("parameters", {})
        for col in t.get("affected_columns", []):
            if col not in result.columns:
                continue
            if strategy == "impute_mean":
                result = _sklearn_impute(result, col, "mean")
            elif strategy == "impute_median":
                result = _sklearn_impute(result, col, "median")
            elif strategy in ("impute_mode", "impute_most_frequent"):
                result = _sklearn_impute(result, col, "most_frequent")
            elif strategy == "impute_constant":
                if "fill_value" not in params:
                    raise ValueError(
                        f"step_5: impute_constant requires 'fill_value' "
                        f"(column {col!r})"
                    )
                result = _sklearn_impute(
                    result, col, "constant", params["fill_value"]
                )
            elif strategy == "impute_unknown":
                fill = params.get("fill_value", "Unknown")
                result[col] = result[col].fillna(fill)

    return result


if __name__ == "__main__":
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "numeric_a": [1.0, 2.0, np.nan, 4.0, np.nan, 6.0],
        "numeric_b": [10.0, np.nan, 30.0, np.nan, 50.0, 60.0],
        "category": ["a", "b", None, "a", "b", None],
        "drop_col": [np.nan, np.nan, np.nan, 1, 2, 3],  # partial missing
    })
    print("Before missing counts:")
    print(df.isna().sum())
    out = step_5_imputation(df, [
        {"strategy": "impute_median", "affected_columns": ["numeric_a"],
         "parameters": {}},
        {"strategy": "impute_mean", "affected_columns": ["numeric_b"],
         "parameters": {}},
        {"strategy": "impute_unknown", "affected_columns": ["category"],
         "parameters": {}},
    ], rng)
    print("\nAfter missing counts:")
    print(out.isna().sum())
    print("\nAfter values:")
    print(out)

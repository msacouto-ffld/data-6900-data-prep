"""Step 2 — Drop all-missing columns.

Strategy: ``drop_column`` — only drops columns that are **actually**
100% missing. Raises if targeted columns have any non-null values,
per the contract's safety rule.
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd


STRATEGIES = {"drop_column"}


def step_2_drop_missing(
    df: pd.DataFrame,
    transformations: List[Dict[str, Any]],
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Drop columns that are 100% missing, per approved transformations.

    Raises
    ------
    ValueError
        If a targeted column has any non-null values (safety rule).
    """
    if not transformations:
        return df

    cols_to_drop: List[str] = []
    for t in transformations:
        strategy = t["strategy"]
        if strategy not in STRATEGIES:
            raise ValueError(
                f"step_2: unknown strategy {strategy!r}. "
                f"Known strategies: {sorted(STRATEGIES)}"
            )
        for col in t.get("affected_columns", []):
            if col not in df.columns:
                # Already dropped by a prior step or never existed —
                # not an error, but log via the execution engine
                continue
            # Safety check: column must be 100% missing
            if not df[col].isna().all():
                raise ValueError(
                    f"step_2: refusing to drop column {col!r} — "
                    f"it has {df[col].notna().sum()} non-null value(s). "
                    "Only 100%-missing columns may be dropped at this step."
                )
            cols_to_drop.append(col)

    if not cols_to_drop:
        return df

    return df.drop(columns=cols_to_drop)


if __name__ == "__main__":
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "keep": [1, 2, 3],
        "drop_me": [None, None, None],
        "also_keep": ["a", "b", "c"],
    })
    print("Before:", list(df.columns))
    out = step_2_drop_missing(
        df,
        [{"strategy": "drop_column", "affected_columns": ["drop_me"],
          "parameters": {}}],
        rng,
    )
    print("After: ", list(out.columns))
    assert list(out.columns) == ["keep", "also_keep"]

    # Safety test: refuse to drop a column with data
    try:
        step_2_drop_missing(
            df,
            [{"strategy": "drop_column", "affected_columns": ["keep"],
              "parameters": {}}],
            rng,
        )
        print("✗ should have raised")
    except ValueError as e:
        print(f"✓ safety check: {e}")

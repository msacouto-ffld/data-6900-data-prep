"""Step 6 — Deduplication.

Strategies:

- ``drop_exact_keep_first`` — ``df.drop_duplicates(keep='first')``
- ``drop_exact_keep_last`` — ``df.drop_duplicates(keep='last')``
- ``keep_most_recent`` — sort by timestamp column, keep most recent
- ``keep_most_complete`` — keep row with fewest NaN values per duplicate group
- ``flag_for_human_review`` — log only, no modification
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd


STRATEGIES = {
    "drop_exact_keep_first",
    "drop_exact_keep_last",
    "keep_most_recent",
    "keep_most_complete",
    "flag_for_human_review",
}


def _keep_most_recent(
    df: pd.DataFrame,
    timestamp_col: str,
    subset: List[str] | None = None,
) -> pd.DataFrame:
    """Keep the most recent row from each duplicate group."""
    if timestamp_col not in df.columns:
        raise ValueError(
            f"step_6: keep_most_recent requires timestamp column "
            f"{timestamp_col!r} which is not in the DataFrame"
        )
    # Stable sort by timestamp descending, then drop duplicates keeping first
    sorted_df = df.sort_values(
        timestamp_col, ascending=False, kind="mergesort"
    )
    dedup = sorted_df.drop_duplicates(subset=subset, keep="first")
    # Restore original row order (preserve determinism)
    return dedup.sort_index()


def _keep_most_complete(
    df: pd.DataFrame,
    subset: List[str] | None = None,
) -> pd.DataFrame:
    """Keep the row with the fewest NaN values per duplicate group."""
    # Compute an auxiliary 'completeness' score per row
    completeness = df.notna().sum(axis=1)
    # Attach to a copy so we can sort by it
    tmp = df.copy()
    tmp["_completeness"] = completeness
    # Sort by completeness descending; mergesort for stability
    sorted_df = tmp.sort_values(
        "_completeness", ascending=False, kind="mergesort"
    )
    dedup = sorted_df.drop_duplicates(subset=subset, keep="first")
    dedup = dedup.drop(columns=["_completeness"])
    return dedup.sort_index()


def step_6_deduplication(
    df: pd.DataFrame,
    transformations: List[Dict[str, Any]],
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Apply approved deduplication transformations."""
    if not transformations:
        return df

    result = df
    for t in transformations:
        strategy = t["strategy"]
        if strategy not in STRATEGIES:
            raise ValueError(
                f"step_6: unknown strategy {strategy!r}. "
                f"Known strategies: {sorted(STRATEGIES)}"
            )
        params = t.get("parameters", {})
        subset = t.get("affected_columns") or None
        # Empty affected_columns means "check all columns" for dedup
        if subset == []:
            subset = None

        if strategy == "drop_exact_keep_first":
            result = result.drop_duplicates(subset=subset, keep="first")
        elif strategy == "drop_exact_keep_last":
            result = result.drop_duplicates(subset=subset, keep="last")
        elif strategy == "keep_most_recent":
            ts_col = params.get("timestamp_column")
            if not ts_col:
                raise ValueError(
                    f"step_6: keep_most_recent requires "
                    f"'timestamp_column' parameter"
                )
            result = _keep_most_recent(result, ts_col, subset)
        elif strategy == "keep_most_complete":
            result = _keep_most_complete(result, subset)
        elif strategy == "flag_for_human_review":
            pass

    # Reset index so downstream steps don't see sparse indices
    return result.reset_index(drop=True)


if __name__ == "__main__":
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "a": [1, 1, 2, 2, 3, 3],
        "b": ["x", "x", "y", "y", "z", "z"],
    })
    print(f"Before: {len(df)} rows")
    out = step_6_deduplication(
        df,
        [{"strategy": "drop_exact_keep_first", "affected_columns": [],
          "parameters": {}}],
        rng,
    )
    print(f"After:  {len(out)} rows (expected 3)")
    assert len(out) == 3
    print("✓ deduplication")

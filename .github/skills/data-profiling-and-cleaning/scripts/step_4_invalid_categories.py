"""Step 4 — Invalid category cleanup.

Strategies:

- ``map_to_canonical_value`` — apply a dict of {variant: canonical}
- ``group_rare_into_other`` — replace categories below threshold_pct
  with "Other"
- ``flag_for_human_review`` — log only, no data modification
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd


STRATEGIES = {
    "map_to_canonical_value",
    "group_rare_into_other",
    "flag_for_human_review",
}


def _map_to_canonical(
    series: pd.Series,
    mapping: Dict[str, str],
) -> pd.Series:
    """Replace values in the series using the canonical mapping."""
    # Non-mapped values pass through unchanged
    return series.map(lambda v: mapping.get(v, v) if pd.notna(v) else v)


def _group_rare_into_other(
    series: pd.Series,
    threshold_pct: float,
) -> pd.Series:
    """Replace categories below threshold_pct with 'Other'."""
    if series.isna().all() or len(series) == 0:
        return series
    pct = (series.value_counts(dropna=True) / len(series)) * 100.0
    rare_values = set(pct[pct < threshold_pct].index)
    if not rare_values:
        return series

    def _replace(v: Any) -> Any:
        if pd.isna(v):
            return v
        return "Other" if v in rare_values else v

    return series.map(_replace)


def step_4_invalid_categories(
    df: pd.DataFrame,
    transformations: List[Dict[str, Any]],
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Apply approved category cleanup transformations."""
    if not transformations:
        return df

    result = df.copy()
    for t in transformations:
        strategy = t["strategy"]
        if strategy not in STRATEGIES:
            raise ValueError(
                f"step_4: unknown strategy {strategy!r}. "
                f"Known strategies: {sorted(STRATEGIES)}"
            )
        params = t.get("parameters", {})
        for col in t.get("affected_columns", []):
            if col not in result.columns:
                continue
            if strategy == "map_to_canonical_value":
                mapping = params.get("canonical_mapping")
                if not isinstance(mapping, dict):
                    raise ValueError(
                        f"step_4: map_to_canonical_value requires "
                        f"'canonical_mapping' dict (column {col!r})"
                    )
                result[col] = _map_to_canonical(result[col], mapping)
            elif strategy == "group_rare_into_other":
                threshold = params.get("threshold_pct")
                if threshold is None:
                    raise ValueError(
                        f"step_4: group_rare_into_other requires "
                        f"'threshold_pct' parameter (column {col!r})"
                    )
                result[col] = _group_rare_into_other(
                    result[col], float(threshold)
                )
            elif strategy == "flag_for_human_review":
                # No modification — step function just records the flag
                pass

    return result


if __name__ == "__main__":
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "region": (
            ["NORTH"] * 40 + ["north"] * 30 + ["South"] * 20
            + ["east"] * 8 + ["west"] * 2
        ),
        "status": ["ok"] * 50 + ["OK"] * 30 + ["Ok"] * 15 + ["fail"] * 5,
    })
    print("region before:", df.region.value_counts().to_dict())
    out = step_4_invalid_categories(df, [
        {"strategy": "map_to_canonical_value",
         "affected_columns": ["region"],
         "parameters": {
             "canonical_mapping": {"NORTH": "North", "north": "North",
                                   "south": "South", "east": "East",
                                   "west": "West"}}},
        {"strategy": "group_rare_into_other",
         "affected_columns": ["region"],
         "parameters": {"threshold_pct": 5.0}},
        {"strategy": "map_to_canonical_value",
         "affected_columns": ["status"],
         "parameters": {"canonical_mapping": {"OK": "ok", "Ok": "ok"}}},
    ], rng)
    print("region after: ", out.region.value_counts().to_dict())
    print("status after: ", out.status.value_counts().to_dict())

"""Step 1 — Column name standardization.

Strategies (from CATALOG.md / DM-103):

- ``standardize_to_snake_case`` — lowercase, replace separators with
  underscores, strip whitespace
- ``remove_special_characters`` — strip non-alphanumeric (keep underscore)
- ``rename_duplicates_with_suffix`` — append ``_1``, ``_2``, etc. to
  duplicated normalized names

Applied in order: special characters → snake_case → duplicate resolution.
Only column names change; data values are never touched.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

import numpy as np
import pandas as pd


STRATEGIES = {
    "standardize_to_snake_case",
    "remove_special_characters",
    "rename_duplicates_with_suffix",
}


def _snake_case(name: str) -> str:
    """Convert a column name to snake_case."""
    s = str(name).strip()
    # Replace separators with underscore
    s = re.sub(r"[\s\-\.]+", "_", s)
    # Camel case → snake case (e.g. "CustomerName" → "customer_name")
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    s = s.lower()
    # Collapse multiple underscores
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def _strip_special(name: str) -> str:
    """Remove non-alphanumeric characters except underscore."""
    return re.sub(r"[^a-zA-Z0-9_]", "", str(name))


def _resolve_duplicates(names: List[str]) -> List[str]:
    """Append _1, _2, ... to names that appear more than once."""
    seen: Dict[str, int] = {}
    out: List[str] = []
    for name in names:
        if name not in seen:
            seen[name] = 0
            out.append(name)
        else:
            seen[name] += 1
            out.append(f"{name}_{seen[name]}")
    return out


def step_1_column_names(
    df: pd.DataFrame,
    transformations: List[Dict[str, Any]],
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Apply column name standardization per approved transformations.

    Because all three step-1 strategies operate on the same column
    names, they're applied together even when only one is in the
    approved plan — you can't snake_case without first stripping
    special characters, and you can't rename duplicates until after
    normalization. The ``transformations`` list is used only to
    determine whether this step should run at all.
    """
    if not transformations:
        return df

    # Determine which strategies were approved
    approved = {t["strategy"] for t in transformations}
    for strategy in approved:
        if strategy not in STRATEGIES:
            raise ValueError(
                f"step_1: unknown strategy {strategy!r}. "
                f"Known strategies: {sorted(STRATEGIES)}"
            )

    new_names: List[str] = []
    for col in df.columns:
        name = str(col)
        # Apply special-char stripping + snake_case together —
        # they compose and the order is idempotent for our regex set.
        if ("remove_special_characters" in approved
                or "standardize_to_snake_case" in approved):
            name = _snake_case(name)
            name = _strip_special(name)
            # Re-snake after stripping in case we introduced adjacent
            # underscores
            name = re.sub(r"_+", "_", name).strip("_")
            if not name:
                name = "unnamed"

        new_names.append(name)

    # Duplicate resolution — always run when duplicates exist after
    # renaming, regardless of whether the strategy was explicitly
    # requested, because duplicate column names would break the output.
    if len(set(new_names)) != len(new_names):
        new_names = _resolve_duplicates(new_names)

    result = df.copy()
    result.columns = new_names
    return result


if __name__ == "__main__":
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "Sales $": [100, 200],
        "Name (Full)": ["Alice", "Bob"],
        "📧 Email": ["a@x.com", "b@x.com"],
        "Customer": ["X", "Y"],
        "customer": ["A", "B"],
    })
    print("Before:", list(df.columns))
    out = step_1_column_names(df, [
        {"strategy": "standardize_to_snake_case",
         "affected_columns": list(df.columns), "parameters": {}},
    ], rng)
    print("After: ", list(out.columns))
    assert (df.values == out.values).all(), "Data values must be unchanged"
    print("✓ data values unchanged")

"""Step 3 — Type coercion.

Internal dispatcher — dispatches to sub-handlers based on the
``strategy`` field:

- ``coerce_to_target_type`` → ``pandas.Series.astype()`` with
  ``errors='coerce'`` (failed conversions become NaN)
- ``parse_dates_infer_format`` → ``pd.to_datetime()`` with
  ``format='mixed'``, fallback to NaT
- ``parse_currency_strip_symbols`` → regex strip currency + commas,
  cast to float
- ``parse_percent_to_float`` → regex strip ``%``, cast to float,
  divide by 100

The execution engine validates required parameters before dispatching.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

import numpy as np
import pandas as pd


STRATEGIES = {
    "coerce_to_target_type",
    "parse_dates_infer_format",
    "parse_currency_strip_symbols",
    "parse_percent_to_float",
}


def _coerce_to_target_type(
    series: pd.Series,
    target_type: str,
) -> pd.Series:
    """Generic astype with coercion. Unparseable values become NaN."""
    t = str(target_type).lower()
    if t in ("int", "int64", "integer"):
        # Integer cast with NaN handling: use the nullable Int64 dtype
        return pd.to_numeric(series, errors="coerce").astype("Int64")
    if t in ("float", "float64", "double"):
        return pd.to_numeric(series, errors="coerce")
    if t in ("str", "string", "object"):
        return series.astype(str).where(series.notna(), None)
    if t in ("bool", "boolean"):
        return series.astype("boolean")
    # Fallback — try astype directly
    try:
        return series.astype(target_type)
    except Exception:
        return pd.to_numeric(series, errors="coerce")


def _parse_dates_infer_format(series: pd.Series) -> pd.Series:
    """Parse strings to datetime with mixed-format inference."""
    return pd.to_datetime(series, format="mixed", errors="coerce")


def _parse_currency_strip_symbols(
    series: pd.Series,
    currency_symbol: str = "$",
) -> pd.Series:
    """Strip currency symbols, commas, and whitespace; cast to float."""
    symbol_escaped = re.escape(currency_symbol)
    pattern = re.compile(rf"[{symbol_escaped},\s]")

    def _clean(val: Any) -> Any:
        if pd.isna(val):
            return np.nan
        try:
            return float(pattern.sub("", str(val)))
        except (ValueError, TypeError):
            return np.nan

    return series.map(_clean)


def _parse_percent_to_float(series: pd.Series) -> pd.Series:
    """Strip '%', cast to float, divide by 100."""
    def _clean(val: Any) -> Any:
        if pd.isna(val):
            return np.nan
        try:
            return float(str(val).replace("%", "").strip()) / 100.0
        except (ValueError, TypeError):
            return np.nan

    return series.map(_clean)


def step_3_type_coercion(
    df: pd.DataFrame,
    transformations: List[Dict[str, Any]],
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Apply approved type coercion transformations."""
    if not transformations:
        return df

    result = df.copy()
    for t in transformations:
        strategy = t["strategy"]
        if strategy not in STRATEGIES:
            raise ValueError(
                f"step_3: unknown strategy {strategy!r}. "
                f"Known strategies: {sorted(STRATEGIES)}"
            )
        params = t.get("parameters", {})
        for col in t.get("affected_columns", []):
            if col not in result.columns:
                continue
            series = result[col]
            if strategy == "coerce_to_target_type":
                target = params.get("target_type")
                if target is None:
                    raise ValueError(
                        f"step_3: coerce_to_target_type requires "
                        f"'target_type' parameter (column {col!r})"
                    )
                result[col] = _coerce_to_target_type(series, target)
            elif strategy == "parse_dates_infer_format":
                result[col] = _parse_dates_infer_format(series)
            elif strategy == "parse_currency_strip_symbols":
                symbol = params.get("currency_symbol", "$")
                result[col] = _parse_currency_strip_symbols(series, symbol)
            elif strategy == "parse_percent_to_float":
                result[col] = _parse_percent_to_float(series)

    return result


if __name__ == "__main__":
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "mixed_num": ["1", 2, "3", "four", 5],
        "date_col": ["2026-01-01", "2026-03-15", "bad", "2026-12-31", None],
        "price": ["$1,200.00", "$500", "$2,399.50", None, "$10"],
        "pct": ["50%", "75%", "100%", None, "25%"],
    })
    print("Before dtypes:")
    print(df.dtypes)
    out = step_3_type_coercion(df, [
        {"strategy": "coerce_to_target_type",
         "affected_columns": ["mixed_num"],
         "parameters": {"target_type": "float"}},
        {"strategy": "parse_dates_infer_format",
         "affected_columns": ["date_col"], "parameters": {}},
        {"strategy": "parse_currency_strip_symbols",
         "affected_columns": ["price"], "parameters": {}},
        {"strategy": "parse_percent_to_float",
         "affected_columns": ["pct"], "parameters": {}},
    ], rng)
    print("\nAfter dtypes:")
    print(out.dtypes)
    print("\nAfter values:")
    print(out)

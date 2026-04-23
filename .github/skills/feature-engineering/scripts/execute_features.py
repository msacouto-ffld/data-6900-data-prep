"""Stage 5 — Execute approved feature transformations.

Pre-built code paths for all 13 transformation methods across
6 batch types. The LLM's ``implementation_hint`` is advisory only —
this script uses trusted, tested implementations.

Contract: contracts/execute-transformations.md
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

try:
    from sklearn.preprocessing import LabelEncoder, MinMaxScaler, StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from mistake_log import log_event


# ---------------------------------------------------------------------------
# Batch 1: Date/Time Extraction
# ---------------------------------------------------------------------------

def _extract_day_of_week(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_datetime(df[col], errors="coerce").dt.dayofweek


def _extract_hour(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_datetime(df[col], errors="coerce").dt.hour


def _extract_month(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_datetime(df[col], errors="coerce").dt.month


def _extract_quarter(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_datetime(df[col], errors="coerce").dt.quarter


# ---------------------------------------------------------------------------
# Batch 2: Text Features
# ---------------------------------------------------------------------------

def _text_string_length(df: pd.DataFrame, col: str) -> pd.Series:
    return df[col].astype(str).str.len()


def _text_word_count(df: pd.DataFrame, col: str) -> pd.Series:
    return df[col].astype(str).str.split().str.len()


# ---------------------------------------------------------------------------
# Batch 3: Aggregate Features
# ---------------------------------------------------------------------------

def _groupby_agg(
    df: pd.DataFrame,
    grouping_key: str,
    source_col: str,
    agg_func: str,
    feat_name: str,
) -> pd.Series:
    """Group-level aggregate mapped back to rows."""
    agg_result = df.groupby(grouping_key)[source_col].agg(agg_func)
    merged = df[[grouping_key]].merge(
        agg_result.rename(feat_name),
        left_on=grouping_key, right_index=True, how="left",
    )
    return merged[feat_name]


# ---------------------------------------------------------------------------
# Batch 4: Derived Columns
# ---------------------------------------------------------------------------

def _derived_ratio(
    df: pd.DataFrame,
    col_a: str,
    col_b: str,
    log_path: str,
    feat_name: str,
) -> pd.Series:
    """col_a / col_b with division-by-zero → NaN."""
    numerator = pd.to_numeric(df[col_a], errors="coerce")
    denominator = pd.to_numeric(df[col_b], errors="coerce")

    # Replace zeros with NaN to avoid division by zero
    zeros = (denominator == 0).sum()
    if zeros > 0:
        log_event(
            log_path, "edge_case_triggered", "execute_transformations",
            f"Division by zero in '{feat_name}': {zeros} rows where "
            f"'{col_b}' = 0. Replaced with NaN.",
            "Replaced with NaN",
            columns=[col_a, col_b],
        )
        denominator = denominator.replace(0, np.nan)

    result = numerator / denominator
    # Replace infinity with NaN
    inf_count = np.isinf(result).sum()
    if inf_count > 0:
        log_event(
            log_path, "edge_case_triggered", "execute_transformations",
            f"Infinity values in '{feat_name}': {inf_count} rows. "
            "Replaced with NaN.",
            "Replaced with NaN",
            columns=[col_a, col_b],
        )
        result = result.replace([np.inf, -np.inf], np.nan)

    return result


def _derived_difference(
    df: pd.DataFrame, col_a: str, col_b: str,
) -> pd.Series:
    return pd.to_numeric(df[col_a], errors="coerce") - \
           pd.to_numeric(df[col_b], errors="coerce")


# ---------------------------------------------------------------------------
# Batch 5: Categorical Encoding
# ---------------------------------------------------------------------------

def _one_hot_encode(
    df: pd.DataFrame,
    col: str,
    feat_prefix: str,
) -> pd.DataFrame:
    """One-hot encode a column. Returns only the new dummy columns."""
    dummies = pd.get_dummies(df[col], prefix=feat_prefix, dtype=int)
    # Ensure column names are snake_case (replace spaces, special chars)
    import re
    clean_cols = {}
    for c in dummies.columns:
        clean = re.sub(r"[^a-zA-Z0-9_]", "_", str(c)).lower()
        clean = re.sub(r"_+", "_", clean).strip("_")
        clean_cols[c] = clean
    dummies = dummies.rename(columns=clean_cols)
    # Sort columns alphabetically per DM-009
    return dummies[sorted(dummies.columns)]


def _label_encode(df: pd.DataFrame, col: str) -> pd.Series:
    """Label encode a column."""
    if SKLEARN_AVAILABLE:
        le = LabelEncoder()
        # Handle NaN by filling temporarily
        filled = df[col].fillna("__NAN__").astype(str)
        encoded = le.fit_transform(filled)
        # Restore NaN where original was NaN
        result = pd.Series(encoded, index=df.index, dtype="Int64")
        result[df[col].isna()] = pd.NA
        return result
    else:
        # Fallback: factorize
        codes, _ = pd.factorize(df[col])
        return pd.Series(codes, index=df.index, dtype="Int64")


# ---------------------------------------------------------------------------
# Batch 6: Normalization / Scaling
# ---------------------------------------------------------------------------

def _min_max_scale(
    df: pd.DataFrame,
    col: str,
    log_path: str,
    feat_name: str,
) -> Optional[pd.Series]:
    """Min-max scale to [0, 1]. Returns None if zero-variance."""
    series = pd.to_numeric(df[col], errors="coerce")
    non_null = series.dropna()
    if len(non_null) == 0:
        return None
    if non_null.std() == 0:
        log_event(
            log_path, "edge_case_triggered", "execute_transformations",
            f"Zero-variance column '{col}' — skipping min-max scaling.",
            "Scaling skipped; documented in report",
            columns=[col],
        )
        return None
    if SKLEARN_AVAILABLE:
        scaler = MinMaxScaler()
        values = series.to_numpy().reshape(-1, 1)
        mask = ~np.isnan(values.ravel())
        result = np.full_like(values.ravel(), np.nan, dtype=float)
        if mask.any():
            result[mask] = scaler.fit_transform(
                values[mask].reshape(-1, 1)
            ).ravel()
        return pd.Series(result, index=df.index)
    else:
        mn, mx = non_null.min(), non_null.max()
        return (series - mn) / (mx - mn)


def _z_score_scale(
    df: pd.DataFrame,
    col: str,
    log_path: str,
    feat_name: str,
) -> Optional[pd.Series]:
    """Z-score standardization. Returns None if zero-variance."""
    series = pd.to_numeric(df[col], errors="coerce")
    non_null = series.dropna()
    if len(non_null) == 0:
        return None
    if non_null.std() == 0:
        log_event(
            log_path, "edge_case_triggered", "execute_transformations",
            f"Zero-variance column '{col}' — skipping z-score scaling.",
            "Scaling skipped; documented in report",
            columns=[col],
        )
        return None
    if SKLEARN_AVAILABLE:
        scaler = StandardScaler()
        values = series.to_numpy().reshape(-1, 1)
        mask = ~np.isnan(values.ravel())
        result = np.full_like(values.ravel(), np.nan, dtype=float)
        if mask.any():
            result[mask] = scaler.fit_transform(
                values[mask].reshape(-1, 1)
            ).ravel()
        return pd.Series(result, index=df.index)
    else:
        return (series - non_null.mean()) / non_null.std()


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

METHOD_MAP = {
    "extract_day_of_week": lambda df, f, lp: _extract_day_of_week(df, f["source_columns"][0]),
    "extract_hour": lambda df, f, lp: _extract_hour(df, f["source_columns"][0]),
    "extract_month": lambda df, f, lp: _extract_month(df, f["source_columns"][0]),
    "extract_quarter": lambda df, f, lp: _extract_quarter(df, f["source_columns"][0]),
    "text_string_length": lambda df, f, lp: _text_string_length(df, f["source_columns"][0]),
    "text_word_count": lambda df, f, lp: _text_word_count(df, f["source_columns"][0]),
    "derived_difference": lambda df, f, lp: _derived_difference(df, f["source_columns"][0], f["source_columns"][1]),
}


def execute_single_feature(
    df: pd.DataFrame,
    feature: Dict[str, Any],
    log_path: str,
) -> Optional[pd.DataFrame]:
    """Execute a single approved feature and return any new columns.

    Returns a DataFrame of new columns to concat, or None if skipped.
    The caller is responsible for adding them to the main DataFrame.
    """
    method = feature["transformation_method"]
    feat_name = feature["feature_name"]  # already has feat_ prefix
    proposed = feature["proposed_name"]
    source_cols = feature.get("source_columns", [])

    try:
        # Special-cased methods that need extra parameters or return
        # multiple columns:

        if method == "groupby_agg":
            key = feature.get("grouping_key")
            agg_func = feature.get("aggregation_function", "sum")
            if not key or not source_cols:
                log_event(
                    log_path, "execution_error", "execute_transformations",
                    f"Missing grouping_key or source_columns for '{feat_name}'",
                    "Feature skipped",
                    columns=source_cols,
                )
                return None
            # The source_col for agg is the value column; grouping_key is separate
            value_col = source_cols[0] if source_cols else key
            series = _groupby_agg(df, key, value_col, agg_func, feat_name)
            return pd.DataFrame({feat_name: series})

        if method == "derived_ratio":
            if len(source_cols) < 2:
                log_event(
                    log_path, "execution_error", "execute_transformations",
                    f"derived_ratio needs 2 source_columns for '{feat_name}'",
                    "Feature skipped",
                    columns=source_cols,
                )
                return None
            series = _derived_ratio(
                df, source_cols[0], source_cols[1], log_path, feat_name,
            )
            return pd.DataFrame({feat_name: series})

        if method == "one_hot_encode":
            col = source_cols[0] if source_cols else None
            if col is None or col not in df.columns:
                return None
            dummies = _one_hot_encode(df, col, feat_name)
            return dummies

        if method == "label_encode":
            col = source_cols[0] if source_cols else None
            if col is None or col not in df.columns:
                return None
            series = _label_encode(df, col)
            return pd.DataFrame({feat_name: series})

        if method == "min_max_scale":
            col = source_cols[0] if source_cols else None
            if col is None or col not in df.columns:
                return None
            series = _min_max_scale(df, col, log_path, feat_name)
            if series is None:
                return None
            return pd.DataFrame({feat_name: series})

        if method == "z_score_scale":
            col = source_cols[0] if source_cols else None
            if col is None or col not in df.columns:
                return None
            series = _z_score_scale(df, col, log_path, feat_name)
            if series is None:
                return None
            return pd.DataFrame({feat_name: series})

        # Simple single-column methods via METHOD_MAP
        if method in METHOD_MAP:
            series = METHOD_MAP[method](df, feature, log_path)
            return pd.DataFrame({feat_name: series})

        # Unknown method — log and skip
        log_event(
            log_path, "execution_error", "execute_transformations",
            f"Unknown transformation_method '{method}' for '{feat_name}'",
            "Feature skipped",
            columns=source_cols,
        )
        return None

    except Exception as exc:
        log_event(
            log_path, "execution_error", "execute_transformations",
            f"Execution error for '{feat_name}': {exc}",
            "Feature skipped; pipeline continues",
            columns=source_cols,
        )
        return None


def execute_all_features(
    df: pd.DataFrame,
    approved_features: List[Dict[str, Any]],
    validation_result: Dict[str, Any],
    log_path: str,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Execute all approved features in batch order.

    Appends new columns to the DataFrame, preserving all originals.
    Writes ``{run_id}-engineered.csv`` to output_dir.
    """
    print("⚙️ Executing approved transformations...")

    # Group by batch
    batches: Dict[int, List[Dict[str, Any]]] = {}
    for f in approved_features:
        bn = f.get("batch_number", 0)
        batches.setdefault(bn, []).append(f)

    batch_names = {
        1: "Date/Time Extraction",
        2: "Text Features",
        3: "Aggregate Features",
        4: "Derived Columns",
        5: "Categorical Encoding",
        6: "Normalization / Scaling",
    }

    result_df = df.copy()
    original_cols = list(df.columns)
    total_new = 0

    for batch_num in range(1, 7):
        features = batches.get(batch_num, [])
        if not features:
            print(f"   Batch {batch_num}: {batch_names.get(batch_num, '?')} — skipped")
            continue

        # Sort alphabetically within batch per DM-009
        features.sort(key=lambda f: f.get("feature_name", ""))

        batch_new = 0
        for feat in features:
            new_cols_df = execute_single_feature(result_df, feat, log_path)
            if new_cols_df is not None and not new_cols_df.empty:
                for col in new_cols_df.columns:
                    result_df[col] = new_cols_df[col].values
                    batch_new += 1

        total_new += batch_new
        if batch_new > 0:
            print(
                f"   Batch {batch_num}: {batch_names.get(batch_num, '?')} "
                f"— {batch_new} features ✅"
            )
        else:
            print(
                f"   Batch {batch_num}: {batch_names.get(batch_num, '?')} "
                "— skipped"
            )

    # Verify original columns preserved
    for col in original_cols:
        if col not in result_df.columns:
            log_event(
                log_path, "execution_error", "execute_transformations",
                f"Original column '{col}' was lost during execution!",
                "Critical — original column missing",
                columns=[col],
            )

    print(
        f"✅ All transformations executed. {total_new} new features created."
    )
    print(
        f"   Output shape: {result_df.shape[0]} rows × "
        f"{result_df.shape[1]} columns"
    )

    # Write CSV
    import os
    run_id = validation_result["run_id"]
    csv_path = os.path.join(output_dir, f"{run_id}-engineered.csv")
    try:
        result_df.to_csv(csv_path, index=False)
    except Exception as exc:
        print(f"❌ Could not write engineered CSV: {exc}")
        log_event(
            log_path, "execution_error", "deliver_outputs",
            f"Failed to write CSV: {exc}",
            "CSV not saved",
        )

    return result_df


if __name__ == "__main__":
    import tempfile, os
    log = os.path.join(tempfile.gettempdir(), "test-exec.md")
    from mistake_log import init_mistake_log
    init_mistake_log(log, "test")

    df = pd.DataFrame({
        "order_date": ["2026-01-01", "2026-01-15", "2026-02-01",
                       "2026-03-10", "2026-03-10"],
        "account_id": ["A", "A", "B", "B", "A"],
        "sale_amount": [100.0, 200.0, 300.0, 400.0, 500.0],
        "units_sold": [10, 20, 0, 40, 50],
        "category": ["premium", "basic", "premium", "basic", "premium"],
        "description": ["good product here", "ok item", "best seller xyz", "short", "another long description text"],
    })

    features = [
        {"feature_name": "feat_day_of_week", "proposed_name": "day_of_week",
         "batch_number": 1, "batch_type": "datetime_extraction",
         "transformation_method": "extract_day_of_week",
         "source_columns": ["order_date"], "description": "Day of week",
         "benchmark_comparison": "Captures cyclicality",
         "confidence_score": 95, "confidence_band": "High"},
        {"feature_name": "feat_word_count", "proposed_name": "word_count",
         "batch_number": 2, "batch_type": "text_features",
         "transformation_method": "text_word_count",
         "source_columns": ["description"], "description": "Word count",
         "benchmark_comparison": "Text length proxy",
         "confidence_score": 95, "confidence_band": "High"},
        {"feature_name": "feat_total_sales", "proposed_name": "total_sales",
         "batch_number": 3, "batch_type": "aggregations",
         "transformation_method": "groupby_agg",
         "source_columns": ["sale_amount"],
         "grouping_key": "account_id",
         "aggregation_function": "sum",
         "description": "Total sales per account",
         "benchmark_comparison": "Account-level metric",
         "confidence_score": 95, "confidence_band": "High"},
        {"feature_name": "feat_revenue_per_unit", "proposed_name": "revenue_per_unit",
         "batch_number": 4, "batch_type": "derived_columns",
         "transformation_method": "derived_ratio",
         "source_columns": ["sale_amount", "units_sold"],
         "description": "Revenue per unit",
         "benchmark_comparison": "Normalizes for order size",
         "confidence_score": 82, "confidence_band": "High"},
        {"feature_name": "feat_category", "proposed_name": "category_encoded",
         "batch_number": 5, "batch_type": "categorical_encoding",
         "transformation_method": "one_hot_encode",
         "source_columns": ["category"],
         "description": "One-hot encoding of category",
         "benchmark_comparison": "Required for modeling",
         "confidence_score": 95, "confidence_band": "High"},
        {"feature_name": "feat_sale_amount_scaled", "proposed_name": "sale_amount_scaled",
         "batch_number": 6, "batch_type": "normalization_scaling",
         "transformation_method": "min_max_scale",
         "source_columns": ["sale_amount"],
         "description": "Min-max scaled sale amount",
         "benchmark_comparison": "Normalizes range",
         "confidence_score": 95, "confidence_band": "High"},
    ]

    vr = {"run_id": "feature-test-0000"}
    result = execute_all_features(df, features, vr, log, tempfile.gettempdir())
    print(f"\nFinal shape: {result.shape}")
    print(f"Columns: {list(result.columns)}")
    print(f"\nfeat_ columns:")
    for c in result.columns:
        if "feat_" in str(c):
            print(f"  {c}: {result[c].tolist()}")
    os.remove(log)

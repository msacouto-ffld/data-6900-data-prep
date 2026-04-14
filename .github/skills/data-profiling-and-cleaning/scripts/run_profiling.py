"""Stage 4 — Run ydata-profiling.

Runs ydata-profiling on the validated DataFrame, exports the HTML report,
and extracts the DM-006 profiling_statistics dict.

Contract: ``contracts/run-profiling.md``
"""
from __future__ import annotations

import os
from typing import Any, Dict, Tuple

import pandas as pd

from schemas import build_dm_005_config


class ProfilingError(Exception):
    """Profiling failure. Caller should halt the pipeline."""


def _safe_float(value: Any) -> float | None:
    """Cast to float if numeric, else None."""
    try:
        if value is None:
            return None
        f = float(value)
        # Guard against NaN/inf leaking into JSON later
        if f != f:  # NaN check
            return None
        return f
    except (TypeError, ValueError):
        return None


def _humanize_bytes(n: float | int | None) -> str:
    """Convert bytes to a short human-readable string."""
    if n is None:
        return "unknown"
    n = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _normalise_type_name(raw: str) -> str:
    """Map a ydata-profiling type label to a DM-006 bucket name."""
    lowered = str(raw).lower()
    if "numeric" in lowered:
        return "numeric"
    if "date" in lowered or "time" in lowered:
        return "datetime"
    if "bool" in lowered:
        return "boolean"
    if "categorical" in lowered or "text" in lowered:
        return "categorical"
    return "other"


def _extract_column_types(table: Dict[str, Any]) -> Dict[str, int]:
    """Normalise the ``table['types']`` dict into DM-006 buckets."""
    raw_types = table.get("types", {}) or {}
    result = {
        "numeric": 0,
        "categorical": 0,
        "datetime": 0,
        "boolean": 0,
        "other": 0,
    }
    for raw_key, count in raw_types.items():
        bucket = _normalise_type_name(raw_key)
        result[bucket] += int(count)
    return result


def _extract_per_column(
    variables: Dict[str, Dict[str, Any]],
    df: pd.DataFrame,
) -> Dict[str, Dict[str, Any]]:
    """Build the DM-006 ``columns`` dict from ``desc.variables``."""
    out: Dict[str, Dict[str, Any]] = {}

    for col_name in df.columns:
        col_name_str = str(col_name)
        # variables is keyed by the original column label; fall back to str
        var = variables.get(col_name)
        if var is None:
            var = variables.get(col_name_str, {})

        col_type = _normalise_type_name(var.get("type", "Unsupported"))

        n_missing = int(var.get("n_missing", 0) or 0)
        # p_missing is a fraction 0–1 in ydata-profiling
        pct_missing_raw = _safe_float(var.get("p_missing", 0)) or 0.0
        pct_missing = pct_missing_raw * 100
        n_unique = int(
            var.get("n_distinct", var.get("n_unique", 0)) or 0
        )
        is_unique = bool(var.get("is_unique", n_unique == len(df)))

        col_entry: Dict[str, Any] = {
            "type": col_type,
            "n_missing": n_missing,
            "pct_missing": round(pct_missing, 2),
            "n_unique": n_unique,
            "is_unique": is_unique,
            "mean": None,
            "std": None,
            "min": None,
            "max": None,
            "median": None,
            "top_values": [],
            "top_frequencies": [],
        }

        if col_type == "numeric":
            col_entry["mean"] = _safe_float(var.get("mean"))
            col_entry["std"] = _safe_float(var.get("std"))
            col_entry["min"] = _safe_float(var.get("min"))
            col_entry["max"] = _safe_float(var.get("max"))
            # ydata uses '50%' for median
            col_entry["median"] = _safe_float(var.get("50%"))
        elif col_type in ("categorical", "other"):
            value_counts = var.get("value_counts_without_nan")
            if value_counts is not None:
                try:
                    top = list(value_counts.head(5).items())
                    col_entry["top_values"] = [str(k) for k, _ in top]
                    col_entry["top_frequencies"] = [int(v) for _, v in top]
                except Exception:
                    pass

        out[col_name_str] = col_entry

    return out


def _extract_correlations(correlations_raw: Any) -> Dict[str, Any]:
    """Extract the Pearson correlation matrix into DM-006 nested dict form.

    In ydata-profiling v4.18.1 ``desc.correlations`` is a dict that may be
    empty in minimal mode. When populated, ``correlations['pearson']`` is a
    pandas DataFrame.
    """
    if not isinstance(correlations_raw, dict):
        return {"pearson": {}}
    pearson = correlations_raw.get("pearson")
    if pearson is None:
        return {"pearson": {}}
    try:
        pearson_dict = pearson.to_dict()
        cleaned: Dict[str, Dict[str, Any]] = {}
        for col_a, row in pearson_dict.items():
            cleaned[str(col_a)] = {}
            for col_b, val in row.items():
                cleaned[str(col_a)][str(col_b)] = _safe_float(val)
        return {"pearson": cleaned}
    except Exception:
        return {"pearson": {}}


def run_profiling(
    df: pd.DataFrame,
    validation_result: Dict[str, Any],
) -> Tuple[Dict[str, Any], str]:
    """Run ydata-profiling and return (profiling_statistics, profiling_mode).

    Also writes the HTML report to ``{run_id}-profile.html`` in the
    current working directory (caller controls cwd).
    """
    try:
        from ydata_profiling import ProfileReport
    except ImportError:
        raise ProfilingError(
            "Pipeline error: ydata-profiling is not available. "
            "Re-run from the beginning."
        )

    cell_count = validation_result["cell_count"]
    filename = validation_result["filename"]
    run_id = validation_result["run_id"]

    config = build_dm_005_config(filename, cell_count)
    mode = "minimal" if config["minimal"] else "full"

    print(f"📊 Running ydata-profiling ({mode} mode)...")
    print("   This may take a moment for larger datasets.")

    try:
        report = ProfileReport(df, **config)
    except Exception as e:
        raise ProfilingError(
            f"Profiling failed: {e}. Please try again in a new session, "
            "or try uploading a smaller sample."
        )

    html_path = f"{run_id}-profile.html"
    try:
        report.to_file(html_path)
    except Exception:
        raise ProfilingError(
            "Profiling error: could not generate HTML report. "
            "Please try again in a new session."
        )

    print("✅ HTML profile report generated.")

    # Extract DM-006 structure from the report description.
    # In ydata-profiling v4.18.1 this is a BaseDescription object with
    # attribute access: desc.table, desc.variables, desc.correlations.
    description = report.get_description()
    table = getattr(description, "table", {}) or {}
    variables = getattr(description, "variables", {}) or {}
    correlations_raw = getattr(description, "correlations", {}) or {}

    n_rows = int(table.get("n", validation_result["row_count"]))
    n_columns = int(table.get("n_var", validation_result["column_count"]))
    n_cells = n_rows * n_columns
    n_missing_cells = int(table.get("n_cells_missing", 0) or 0)
    pct_missing_cells = _safe_float(table.get("p_cells_missing", 0)) or 0.0
    if pct_missing_cells <= 1:
        pct_missing_cells *= 100
    n_duplicate = int(table.get("n_duplicates", 0) or 0)
    pct_duplicate = _safe_float(table.get("p_duplicates", 0)) or 0.0
    if pct_duplicate <= 1:
        pct_duplicate *= 100
    memory_bytes = table.get("memory_size")

    profiling_statistics: Dict[str, Any] = {
        "profiling_mode": mode,
        "dataset": {
            "n_rows": n_rows,
            "n_columns": n_columns,
            "n_cells": n_cells,
            "n_missing_cells": n_missing_cells,
            "pct_missing_cells": round(pct_missing_cells, 2),
            "n_duplicate_rows": n_duplicate,
            "pct_duplicate_rows": round(pct_duplicate, 2),
            "memory_size": _humanize_bytes(memory_bytes),
            "types": _extract_column_types(table),
        },
        "columns": _extract_per_column(variables, df),
        "correlations": _extract_correlations(correlations_raw),
    }

    # Confirm HTML exists and is non-empty
    if not os.path.isfile(html_path) or os.path.getsize(html_path) == 0:
        raise ProfilingError(
            "Profiling error: could not generate HTML report. "
            "Please try again in a new session."
        )

    return profiling_statistics, mode


if __name__ == "__main__":
    import json
    import sys
    from validate_input import validate_input
    from detect_quality_issues import detect_quality_issues

    if len(sys.argv) != 2:
        print("Usage: python run_profiling.py <path-to-csv>")
        sys.exit(1)

    df, vr = validate_input(sys.argv[1])
    detect_quality_issues(df, vr)
    stats, mode = run_profiling(df, vr)
    print(f"\nMode: {mode}")
    print(f"Dataset: {stats['dataset']['n_rows']}×{stats['dataset']['n_columns']}")
    print(f"Missing cells: {stats['dataset']['n_missing_cells']} "
          f"({stats['dataset']['pct_missing_cells']}%)")
    print(f"Types: {stats['dataset']['types']}")
    print(f"Column count: {len(stats['columns'])}")
    # Show first numeric column
    for name, col in stats["columns"].items():
        if col["type"] == "numeric":
            print(f"First numeric ({name}): mean={col['mean']}, "
                  f"std={col['std']}, min={col['min']}, max={col['max']}")
            break

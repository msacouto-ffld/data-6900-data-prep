"""Stage 6 — Generate inline charts via matplotlib.

Generates 3 charts for display alongside the NL report:

- Missing values bar (omit if zero missing)
- Data type distribution bar (always included)
- Numeric histograms grid (omit if no numeric columns; cap at top 12 by variance)

Chart failures are non-blocking — if a chart fails, set ``included: false``
and continue. The NL report adapts its references based on the metadata.

Contract: ``contracts/generate-charts.md``
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

import pandas as pd


# Non-interactive backend — required for sandbox execution
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # noqa: E402
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


def _apply_style() -> None:
    """Apply the contract's style preference with graceful fallback."""
    if not MATPLOTLIB_AVAILABLE:
        return
    try:
        plt.style.use("seaborn-v0_8-whitegrid")
    except (OSError, ValueError):
        try:
            plt.style.use("seaborn-whitegrid")
        except (OSError, ValueError):
            pass  # matplotlib default


def _make_metadata_entry(
    chart_type: str,
    filename: str,
    file_path: str,
    included: bool,
    description: str,
    note: str | None = None,
) -> Dict[str, Any]:
    """Build a DM-007 chart metadata entry."""
    return {
        "chart_type": chart_type,
        "filename": filename,
        "file_path": file_path,
        "included": included,
        "description": description,
        "note": note,
    }


def _generate_missing_values_chart(
    df: pd.DataFrame,
    run_id: str,
) -> Dict[str, Any]:
    """Horizontal bar of per-column missing percentages (>0% only)."""
    filename = f"{run_id}-chart-missing.png"
    file_path = os.path.abspath(filename)

    missing_pct = (df.isnull().mean() * 100)
    missing_pct = missing_pct[missing_pct > 0].sort_values(ascending=True)

    if missing_pct.empty:
        return _make_metadata_entry(
            "missing_values", filename, file_path, False,
            "Missing values bar chart (omitted — no missing values).",
        )

    try:
        fig, ax = plt.subplots(
            figsize=(8, max(3, 0.35 * len(missing_pct) + 1)),
            dpi=150,
        )
        ax.barh(missing_pct.index.astype(str), missing_pct.values)
        ax.set_xlabel("Missing (%)", fontsize=10)
        ax.set_title("Missing Values by Column", fontsize=12)
        for i, (col, pct) in enumerate(missing_pct.items()):
            ax.text(pct, i, f"  {pct:.1f}%", va="center", fontsize=9)
        ax.set_xlim(0, max(missing_pct.values) * 1.18)
        fig.tight_layout()
        fig.savefig(file_path, bbox_inches="tight")
        plt.close(fig)
    except Exception as exc:
        print(f"   ⚠️ Missing values chart failed: {exc}")
        return _make_metadata_entry(
            "missing_values", filename, file_path, False,
            "Missing values bar chart (generation failed).",
        )

    return _make_metadata_entry(
        "missing_values", filename, file_path, True,
        "Horizontal bar chart showing percentage of missing values per column.",
    )


def _generate_dtype_distribution_chart(
    df: pd.DataFrame,
    run_id: str,
) -> Dict[str, Any]:
    """Vertical bar of dtype counts (always included)."""
    filename = f"{run_id}-chart-dtypes.png"
    file_path = os.path.abspath(filename)

    dtype_counts = df.dtypes.astype(str).value_counts()

    try:
        fig, ax = plt.subplots(figsize=(7, 4), dpi=150)
        ax.bar(dtype_counts.index, dtype_counts.values)
        ax.set_ylabel("Number of Columns", fontsize=10)
        ax.set_title("Data Type Distribution", fontsize=12)
        for i, count in enumerate(dtype_counts.values):
            ax.text(i, count, f"{count}", ha="center", va="bottom", fontsize=9)
        ax.set_ylim(0, max(dtype_counts.values) * 1.15)
        fig.tight_layout()
        fig.savefig(file_path, bbox_inches="tight")
        plt.close(fig)
    except Exception as exc:
        print(f"   ⚠️ Data type chart failed: {exc}")
        return _make_metadata_entry(
            "dtype_distribution", filename, file_path, False,
            "Data type distribution bar chart (generation failed).",
        )

    return _make_metadata_entry(
        "dtype_distribution", filename, file_path, True,
        "Bar chart showing the count of columns per data type.",
    )


def _generate_numeric_histograms_chart(
    df: pd.DataFrame,
    run_id: str,
) -> Dict[str, Any]:
    """Grid of numeric histograms (capped at top 12 by variance)."""
    filename = f"{run_id}-chart-histograms.png"
    file_path = os.path.abspath(filename)

    numeric_df = df.select_dtypes(include="number")
    if numeric_df.empty:
        return _make_metadata_entry(
            "numeric_histograms", filename, file_path, False,
            "Numeric histograms (omitted — no numeric columns).",
        )

    total_numeric = numeric_df.shape[1]
    # Cap at top 12 by variance
    note: str | None = None
    if total_numeric > 12:
        variances = numeric_df.var(numeric_only=True).sort_values(
            ascending=False
        )
        top_cols = variances.head(12).index.tolist()
        numeric_df = numeric_df[top_cols]
        note = (
            f"Showing top 12 of {total_numeric} numeric columns by variance."
        )

    n_cols = numeric_df.shape[1]
    cols_per_row = min(4, n_cols)
    n_rows = (n_cols + cols_per_row - 1) // cols_per_row

    try:
        fig, axes = plt.subplots(
            n_rows, cols_per_row,
            figsize=(cols_per_row * 3.2, n_rows * 2.6),
            dpi=150,
            squeeze=False,
        )
        axes_flat = axes.flatten()
        for i, col in enumerate(numeric_df.columns):
            ax = axes_flat[i]
            series = numeric_df[col].dropna()
            if len(series) == 0:
                ax.set_visible(False)
                continue
            ax.hist(series, bins=30)
            ax.set_title(str(col), fontsize=10)
            ax.tick_params(axis="both", labelsize=8)
        # Hide any unused subplots
        for j in range(n_cols, len(axes_flat)):
            axes_flat[j].set_visible(False)
        fig.suptitle("Numeric Column Distributions", fontsize=12)
        fig.tight_layout()
        fig.savefig(file_path, bbox_inches="tight")
        plt.close(fig)
    except Exception as exc:
        print(f"   ⚠️ Numeric histograms chart failed: {exc}")
        return _make_metadata_entry(
            "numeric_histograms", filename, file_path, False,
            "Numeric histograms (generation failed).",
        )

    description = (
        f"Grid of histograms showing the distribution of "
        f"{n_cols} numeric column(s), 30 bins each."
    )
    return _make_metadata_entry(
        "numeric_histograms", filename, file_path, True,
        description, note,
    )


def generate_charts(
    df: pd.DataFrame,
    validation_result: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Generate the 3 charts. Returns the DM-007 metadata list."""
    run_id = validation_result["run_id"]

    if not MATPLOTLIB_AVAILABLE:
        print(
            "⚠️ Chart generation error: matplotlib is not available. "
            "Charts will be skipped."
        )
        return [
            _make_metadata_entry(
                "missing_values",
                f"{run_id}-chart-missing.png",
                "", False, "matplotlib unavailable",
            ),
            _make_metadata_entry(
                "dtype_distribution",
                f"{run_id}-chart-dtypes.png",
                "", False, "matplotlib unavailable",
            ),
            _make_metadata_entry(
                "numeric_histograms",
                f"{run_id}-chart-histograms.png",
                "", False, "matplotlib unavailable",
            ),
        ]

    print("📈 Generating visualizations...")
    _apply_style()

    metadata: List[Dict[str, Any]] = []
    for generator, label in (
        (_generate_missing_values_chart, "Missing values chart"),
        (_generate_dtype_distribution_chart, "Data type distribution chart"),
        (_generate_numeric_histograms_chart, "Numeric histograms"),
    ):
        entry = generator(df, run_id)
        metadata.append(entry)
        if entry["included"]:
            print(f"   ✅ {label}")
        else:
            print(f"   ℹ️ {label} (omitted)")

    return metadata


if __name__ == "__main__":
    import sys
    from validate_input import validate_input

    if len(sys.argv) != 2:
        print("Usage: python generate_charts.py <path-to-csv>")
        sys.exit(1)

    df, vr = validate_input(sys.argv[1])
    metadata = generate_charts(df, vr)
    print("\nChart metadata:")
    for m in metadata:
        included = "✅" if m["included"] else "❌"
        print(f"  {included} {m['chart_type']}: {m['filename']}")
        if m.get("note"):
            print(f"     note: {m['note']}")

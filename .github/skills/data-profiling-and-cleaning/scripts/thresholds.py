"""DM-108 high-impact thresholds.

These constants trigger high-impact flags during execution. The
:func:`check_high_impact` function in ``high_impact.py`` reads them
and compares them against actual per-step metrics to decide whether
to raise a flag.

Tunable: if you need to adjust defaults, update this file. Each
threshold is documented in the transformation report when triggered
with both the actual value and the threshold, so auditability is
preserved even as values change.
"""
from __future__ import annotations

from typing import Any, Dict


HIGH_IMPACT_THRESHOLDS: Dict[str, Any] = {
    # Any step that removes more than 10% of rows is high-impact
    "row_reduction_pct": 10.0,

    # Dropping any column is always high-impact (boolean gate)
    "column_dropped": True,

    # Imputing more than 30% of a column's values is high-impact
    "imputation_pct": 30.0,

    # Modifying more than 5% of rows via outlier treatment is high-impact
    "outlier_treatment_pct": 5.0,

    # Mean shift of more than 15% in a column post-transformation is
    # high-impact (flags unexpected distribution changes)
    "mean_shift_pct": 15.0,

    # Any coercion that produces NaN values from previously non-null
    # data is high-impact (boolean gate)
    "coercion_data_loss": True,

    # Replacing more than 10% of categorical values (e.g. group_rare_into_other)
    # is high-impact
    "category_replacement_pct": 10.0,
}


def get_threshold(name: str) -> Any:
    """Look up a threshold by name."""
    if name not in HIGH_IMPACT_THRESHOLDS:
        raise KeyError(
            f"Unknown high-impact threshold: {name!r}. "
            f"Known: {sorted(HIGH_IMPACT_THRESHOLDS)}"
        )
    return HIGH_IMPACT_THRESHOLDS[name]


if __name__ == "__main__":
    for k, v in HIGH_IMPACT_THRESHOLDS.items():
        print(f"  {k}: {v}")

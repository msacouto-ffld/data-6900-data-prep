"""DM-103 transformation catalog.

The single source of truth for which strategies the execution engine
dispatches to. The LLM proposer also embeds this catalog in its system
prompt (via CATALOG.md), so both must stay in sync.

If you add a strategy here, you also need to:

1. Add it to CATALOG.md
2. Add its required parameters to ``REQUIRED_PARAMETERS`` below
3. Implement its handling in the appropriate ``step_N_*.py`` module
4. Update ``propose_transformations`` prompt in PROMPTS.md to describe it
"""
from __future__ import annotations

from typing import Dict, List, Set


TRANSFORMATION_CATALOG: Dict[int, Dict[str, object]] = {
    1: {
        "step_name": "column_name_standardization",
        "strategies": [
            "standardize_to_snake_case",
            "remove_special_characters",
            "rename_duplicates_with_suffix",
        ],
    },
    2: {
        "step_name": "drop_all_missing_columns",
        "strategies": [
            "drop_column",
        ],
    },
    3: {
        "step_name": "type_coercion",
        "strategies": [
            "coerce_to_target_type",
            "parse_dates_infer_format",
            "parse_currency_strip_symbols",
            "parse_percent_to_float",
        ],
    },
    4: {
        "step_name": "invalid_category_cleanup",
        "strategies": [
            "map_to_canonical_value",
            "group_rare_into_other",
            "flag_for_human_review",
        ],
    },
    5: {
        "step_name": "missing_value_imputation",
        "strategies": [
            "drop_rows",
            "drop_column",
            "impute_mean",
            "impute_median",
            "impute_mode",
            "impute_constant",
            "impute_most_frequent",
            "impute_unknown",
        ],
    },
    6: {
        "step_name": "deduplication",
        "strategies": [
            "drop_exact_keep_first",
            "drop_exact_keep_last",
            "keep_most_recent",
            "keep_most_complete",
            "flag_for_human_review",
        ],
    },
    7: {
        "step_name": "outlier_treatment",
        "strategies": [
            "cap_at_percentile",
            "remove_rows",
            "flag_only",
            "winsorize",
        ],
    },
}


# Required parameters per strategy — enforced by execute_transformations
# before dispatching to a step function. Strategies not in this dict
# have no required parameters.
REQUIRED_PARAMETERS: Dict[str, List[str]] = {
    "coerce_to_target_type": ["target_type"],
    "impute_constant": ["fill_value"],
    "map_to_canonical_value": ["canonical_mapping"],
    "group_rare_into_other": ["threshold_pct"],
    "cap_at_percentile": ["percentile_lower", "percentile_upper"],
    "winsorize": ["percentile_lower", "percentile_upper"],
}


def get_step_name(step: int) -> str:
    """Return the canonical step name for a step number."""
    return str(TRANSFORMATION_CATALOG[step]["step_name"])


def get_strategies_for_step(step: int) -> List[str]:
    """Return the list of approved strategy names for a step."""
    return list(TRANSFORMATION_CATALOG[step]["strategies"])  # type: ignore


def all_strategies() -> Set[str]:
    """Return the flat set of every approved strategy across all steps."""
    result: Set[str] = set()
    for step_info in TRANSFORMATION_CATALOG.values():
        result.update(step_info["strategies"])  # type: ignore
    return result


def get_required_parameters(strategy: str) -> List[str]:
    """Return the list of required parameter names for a strategy."""
    return list(REQUIRED_PARAMETERS.get(strategy, []))


def validate_transformation_parameters(
    strategy: str,
    parameters: Dict[str, object],
) -> List[str]:
    """Check a transformation's parameters for missing required keys.

    Returns a list of missing parameter names (empty if all present).
    Used by ``execute_transformations`` before dispatching a step.
    """
    required = get_required_parameters(strategy)
    return [p for p in required if p not in parameters]


if __name__ == "__main__":
    # Sanity checks
    print(f"Total strategies: {len(all_strategies())}")
    print(f"Step 3 strategies: {get_strategies_for_step(3)}")
    print(
        f"Required for impute_constant: "
        f"{get_required_parameters('impute_constant')}"
    )
    missing = validate_transformation_parameters(
        "cap_at_percentile", {"percentile_lower": 1.0},
    )
    print(f"Missing for cap_at_percentile with only lower: {missing}")

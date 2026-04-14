"""Feature 2 data schemas — DM-101 through DM-113.

Covers every schema from Feature 2's data-model.md as typed dict
templates with validation helpers. Pattern matches Feature 1's
``schemas.py``: every validator returns a list of violation strings
rather than raising, so callers can accumulate errors before deciding
whether to halt.

Reference: ``specs/002-imputation-feature2/data-model.md``
"""
from __future__ import annotations

from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# DM-101 — Feature 1 inputs (reproduced from Feature 1's DM-010)
# ---------------------------------------------------------------------------

DM_101_REQUIRED_KEYS = {
    "run_id",
    "filename",
    "validated_at",
    "profiling_mode",
    "validation_result",
    "quality_detections",
    "pii_scan",
    "profiling_statistics",
}


def validate_dm_101(obj: Dict[str, Any]) -> List[str]:
    """Validate the Feature 1 JSON handoff on load."""
    violations: List[str] = []
    if not isinstance(obj, dict):
        return [f"DM-101: expected dict, got {type(obj).__name__}"]
    for key in DM_101_REQUIRED_KEYS:
        if key not in obj:
            violations.append(f"DM-101: missing top-level key '{key}'")
    if "run_id" in obj and isinstance(obj["run_id"], str):
        if not obj["run_id"].startswith("profile-"):
            violations.append(
                "DM-101: run_id must start with 'profile-' "
                "(did Feature 1 produce this file?)"
            )
    return violations


# ---------------------------------------------------------------------------
# DM-102 — Transformation run metadata
# ---------------------------------------------------------------------------

DM_102_REQUIRED_KEYS = {
    "transform_run_id": str,
    "source_profiling_run_id": str,
    "original_filename": str,
    "original_file_path": str,
    "started_at": str,
    "random_seed": int,
    "pipeline_version": str,
}


def validate_dm_102(obj: Dict[str, Any]) -> List[str]:
    """Validate the run metadata dict."""
    violations: List[str] = []
    if not isinstance(obj, dict):
        return [f"DM-102: expected dict, got {type(obj).__name__}"]
    for key, expected_type in DM_102_REQUIRED_KEYS.items():
        if key not in obj:
            violations.append(f"DM-102: missing key '{key}'")
            continue
        if not isinstance(obj[key], expected_type):
            violations.append(
                f"DM-102: key '{key}' should be "
                f"{expected_type.__name__}, got {type(obj[key]).__name__}"
            )
    if "transform_run_id" in obj and isinstance(obj["transform_run_id"], str):
        if not obj["transform_run_id"].startswith("transform-"):
            violations.append(
                "DM-102: transform_run_id must start with 'transform-'"
            )
    if "random_seed" in obj and obj["random_seed"] != 42:
        violations.append("DM-102: random_seed must be 42 for determinism")
    return violations


# ---------------------------------------------------------------------------
# DM-104 — Transformation plan (LLM output from propose_transformations)
# ---------------------------------------------------------------------------

DM_104_TOP_LEVEL_KEYS = {
    "plan_id",
    "source_profiling_run_id",
    "no_issues_detected",
    "transformations",
}


def validate_dm_104(obj: Dict[str, Any]) -> List[str]:
    """Validate the transformation plan output from the LLM."""
    violations: List[str] = []
    if not isinstance(obj, dict):
        return [f"DM-104: expected dict, got {type(obj).__name__}"]
    for key in DM_104_TOP_LEVEL_KEYS:
        if key not in obj:
            violations.append(f"DM-104: missing top-level key '{key}'")
    if "transformations" in obj:
        if not isinstance(obj["transformations"], list):
            violations.append("DM-104: transformations must be a list")
        else:
            for i, t in enumerate(obj["transformations"]):
                violations.extend(_validate_dm_104_transformation(t, i))
    # no_issues_detected: if True, transformations should be empty
    if obj.get("no_issues_detected") is True:
        if obj.get("transformations"):
            violations.append(
                "DM-104: no_issues_detected is True but transformations "
                "list is non-empty"
            )
    return violations


def _validate_dm_104_transformation(t: Any, i: int) -> List[str]:
    """Validate a single transformation entry inside DM-104."""
    violations: List[str] = []
    if not isinstance(t, dict):
        return [f"DM-104[{i}]: expected dict"]
    required = {
        "id", "step", "step_name", "issue", "affected_columns",
        "strategy", "is_custom", "justification", "expected_impact",
        "parameters",
    }
    for key in required:
        if key not in t:
            violations.append(f"DM-104[{i}]: missing key '{key}'")
    step = t.get("step")
    if not isinstance(step, int) or not (1 <= step <= 7):
        violations.append(
            f"DM-104[{i}]: step must be integer 1–7, got {step}"
        )
    if not isinstance(t.get("affected_columns", []), list):
        violations.append(f"DM-104[{i}]: affected_columns must be a list")
    if not isinstance(t.get("is_custom"), bool):
        violations.append(f"DM-104[{i}]: is_custom must be bool")
    if not isinstance(t.get("parameters", {}), dict):
        violations.append(f"DM-104[{i}]: parameters must be a dict")
    return violations


# ---------------------------------------------------------------------------
# DM-105 — Review panel output
# ---------------------------------------------------------------------------

DM_105_VERDICTS = {"APPROVE", "REJECT"}
DM_105_FIXED_SCORES = {95, 82, 67, 50, 35}
DM_105_BANDS = {"High", "Medium", "Low"}

SCORE_TO_BAND = {
    95: "High",
    82: "High",
    67: "Medium",
    50: "Medium",
    35: "Low",
}


def validate_dm_105(obj: Dict[str, Any]) -> List[str]:
    """Validate a review_output dict from the LLM review panel."""
    violations: List[str] = []
    if not isinstance(obj, dict):
        return [f"DM-105: expected dict, got {type(obj).__name__}"]
    for key in ("review_id", "round", "reviews", "overall_summary"):
        if key not in obj:
            violations.append(f"DM-105: missing top-level key '{key}'")
    reviews = obj.get("reviews", [])
    if not isinstance(reviews, list):
        violations.append("DM-105: reviews must be a list")
        return violations
    for i, r in enumerate(reviews):
        if not isinstance(r, dict):
            violations.append(f"DM-105.reviews[{i}]: expected dict")
            continue
        for key in ("transformation_id", "step", "verdict",
                    "confidence_score", "confidence_band"):
            if key not in r:
                violations.append(
                    f"DM-105.reviews[{i}]: missing key '{key}'"
                )
        if r.get("verdict") not in DM_105_VERDICTS:
            violations.append(
                f"DM-105.reviews[{i}]: verdict must be APPROVE/REJECT"
            )
        score = r.get("confidence_score")
        if score not in DM_105_FIXED_SCORES:
            violations.append(
                f"DM-105.reviews[{i}]: confidence_score must be one of "
                f"{sorted(DM_105_FIXED_SCORES)}, got {score}"
            )
        band = r.get("confidence_band")
        if band not in DM_105_BANDS:
            violations.append(
                f"DM-105.reviews[{i}]: confidence_band must be in "
                f"{sorted(DM_105_BANDS)}, got {band}"
            )
        # Score-to-band consistency
        if score in SCORE_TO_BAND and band and band != SCORE_TO_BAND[score]:
            violations.append(
                f"DM-105.reviews[{i}]: score {score} should map to "
                f"band {SCORE_TO_BAND[score]}, got {band}"
            )
    return violations


# ---------------------------------------------------------------------------
# DM-106 — Approved plan (merged DM-104 + DM-105)
# ---------------------------------------------------------------------------

DM_106_TOP_LEVEL_KEYS = {
    "approved_transformations",
    "rejected_transformations",
    "skipped_transformations",
    "human_review_decisions",
    "dependency_warnings",
}

# Step dependency map — which steps depend on which
STEP_DEPENDENCY_MAP = {
    3: [1],      # type coercion depends on column names
    4: [3],      # invalid categories depends on types
    5: [3],      # imputation depends on types
    6: [5],      # deduplication depends on imputation
    7: [3, 5],   # outliers depends on types AND imputation
}


def validate_dm_106(obj: Dict[str, Any]) -> List[str]:
    """Validate the approved plan structure."""
    violations: List[str] = []
    if not isinstance(obj, dict):
        return [f"DM-106: expected dict, got {type(obj).__name__}"]
    for key in DM_106_TOP_LEVEL_KEYS:
        if key not in obj:
            violations.append(f"DM-106: missing top-level key '{key}'")
        elif not isinstance(obj[key], list):
            violations.append(f"DM-106: '{key}' must be a list")
    return violations


# ---------------------------------------------------------------------------
# DM-107 — Step execution result
# ---------------------------------------------------------------------------

DM_107_REQUIRED_KEYS = {"step", "step_name", "transformations_applied",
                         "metrics_before", "metrics_after",
                         "high_impact_flags", "skipped"}


def validate_dm_107(obj: Dict[str, Any]) -> List[str]:
    """Validate a single step execution result."""
    violations: List[str] = []
    if not isinstance(obj, dict):
        return [f"DM-107: expected dict, got {type(obj).__name__}"]
    for key in DM_107_REQUIRED_KEYS:
        if key not in obj:
            violations.append(f"DM-107: missing key '{key}'")
    step = obj.get("step")
    if not isinstance(step, int) or not (1 <= step <= 7):
        violations.append(f"DM-107: step must be integer 1–7, got {step}")
    if not isinstance(obj.get("skipped"), bool):
        violations.append("DM-107: skipped must be bool")
    return violations


# ---------------------------------------------------------------------------
# DM-110 — Transformation metadata JSON (Skill B handoff)
# ---------------------------------------------------------------------------

DM_110_REQUIRED_KEYS = {
    "run_id", "source_profiling_run_id", "original_filename",
    "produced_by", "pipeline_version", "row_count_before",
    "row_count_after", "column_count_before", "column_count_after",
    "columns", "transformations", "pii_warnings",
    "skipped_transformations", "handoff_contract_version",
}


def validate_dm_110(obj: Dict[str, Any]) -> List[str]:
    """Validate the Skill B handoff metadata."""
    violations: List[str] = []
    if not isinstance(obj, dict):
        return [f"DM-110: expected dict, got {type(obj).__name__}"]
    for key in DM_110_REQUIRED_KEYS:
        if key not in obj:
            violations.append(f"DM-110: missing key '{key}'")
    if obj.get("produced_by") != "skill_a":
        violations.append(
            f"DM-110: produced_by must be 'skill_a', "
            f"got {obj.get('produced_by')!r}"
        )
    if obj.get("handoff_contract_version") != "1.0":
        violations.append(
            f"DM-110: handoff_contract_version must be '1.0', "
            f"got {obj.get('handoff_contract_version')!r}"
        )
    if "run_id" in obj and isinstance(obj["run_id"], str):
        if not obj["run_id"].startswith("transform-"):
            violations.append("DM-110: run_id must start with 'transform-'")
    return violations


# ---------------------------------------------------------------------------
# DM-112 — Mistake log
# ---------------------------------------------------------------------------

DM_112_ENTRY_TYPES = {
    "persona_rejection",
    "execution_error",
    "edge_case_warning",
    "consensus_failure",
    "high_impact_flag",
    "human_review_decision",
}


def validate_dm_112(obj: Dict[str, Any]) -> List[str]:
    """Validate the mistake log structure."""
    violations: List[str] = []
    if not isinstance(obj, dict):
        return [f"DM-112: expected dict, got {type(obj).__name__}"]
    for key in ("run_id", "feature", "timestamp", "entries"):
        if key not in obj:
            violations.append(f"DM-112: missing key '{key}'")
    if obj.get("feature") != "002-data-transformation":
        violations.append(
            "DM-112: feature must be '002-data-transformation'"
        )
    entries = obj.get("entries", [])
    if not isinstance(entries, list):
        violations.append("DM-112: entries must be a list")
        return violations
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            violations.append(f"DM-112.entries[{i}]: expected dict")
            continue
        if entry.get("type") not in DM_112_ENTRY_TYPES:
            violations.append(
                f"DM-112.entries[{i}]: type must be one of "
                f"{sorted(DM_112_ENTRY_TYPES)}"
            )
        if not isinstance(entry.get("step"), int):
            violations.append(f"DM-112.entries[{i}]: step must be int")
    return violations


if __name__ == "__main__":
    # Smoke test
    sample_metadata = {
        "transform_run_id": "transform-20260414-000000-abcd",
        "source_profiling_run_id": "profile-20260404-000000-ef01",
        "original_filename": "test.csv",
        "original_file_path": "/tmp/test.csv",
        "started_at": "2026-04-14T00:00:00",
        "random_seed": 42,
        "pipeline_version": "1.0",
    }
    print("DM-102 violations:", validate_dm_102(sample_metadata))

    sample_plan = {
        "plan_id": "transform-20260414-000000-abcd-plan",
        "source_profiling_run_id": "profile-20260404-000000-ef01",
        "no_issues_detected": False,
        "transformations": [
            {
                "id": "t-1-01",
                "step": 1,
                "step_name": "column_name_standardization",
                "issue": "special_characters: 2 columns have special chars",
                "affected_columns": ["Sales $", "Name (Full)"],
                "strategy": "standardize_to_snake_case",
                "is_custom": False,
                "justification": "Normalise non-standard names",
                "expected_impact": "Columns renamed to snake_case",
                "parameters": {},
            }
        ],
    }
    print("DM-104 violations:", validate_dm_104(sample_plan))

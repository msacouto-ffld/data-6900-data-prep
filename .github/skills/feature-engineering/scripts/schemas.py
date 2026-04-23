"""Skill B schemas — DM-001 through DM-012.

Validators return lists of violation strings (empty = valid).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# DM-001 validation rules (hardcoded checks on the DataFrame)
# ---------------------------------------------------------------------------

SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9_]*$")

CONFIDENCE_SCORES = {95, 82, 67, 50, 35}
SCORE_TO_BAND = {95: "High", 82: "High", 67: "Medium", 50: "Medium", 35: "Low"}

BATCH_TYPES = {
    "datetime_extraction",
    "text_features",
    "aggregations",
    "derived_columns",
    "categorical_encoding",
    "normalization_scaling",
}

TRANSFORMATION_METHODS = {
    "extract_day_of_week", "extract_hour", "extract_month", "extract_quarter",
    "text_string_length", "text_word_count",
    "groupby_agg",
    "derived_ratio", "derived_difference",
    "one_hot_encode", "label_encode",
    "min_max_scale", "z_score_scale",
}

PERSONA_TYPES = {
    "feature_relevance_skeptic",
    "statistical_reviewer",
    "domain_expert",
}

EVENT_TYPES = {
    "handoff_contract_violation", "handoff_contract_warning",
    "pii_warning", "persona_rejection", "persona_modification",
    "edge_case_triggered", "execution_error",
    "verification_correction", "verification_issue",
    "jargon_scan_flag",
}


# ---------------------------------------------------------------------------
# DM-003 — Validation result
# ---------------------------------------------------------------------------

DM_003_REQUIRED = {
    "run_id", "filename", "file_path", "row_count", "column_count",
    "cell_count", "column_names", "column_dtypes",
    "has_metadata_json", "has_transformation_report",
    "metadata_provenance_valid", "pii_flags", "warnings", "validated_at",
}


def validate_dm_003(obj: Dict[str, Any]) -> List[str]:
    violations: List[str] = []
    if not isinstance(obj, dict):
        return ["DM-003: expected dict"]
    for k in DM_003_REQUIRED:
        if k not in obj:
            violations.append(f"DM-003: missing '{k}'")
    if "run_id" in obj and isinstance(obj["run_id"], str):
        if not obj["run_id"].startswith("feature-"):
            violations.append("DM-003: run_id must start with 'feature-'")
    return violations


# ---------------------------------------------------------------------------
# DM-004 — Dataset summary
# ---------------------------------------------------------------------------

DM_004_REQUIRED = {
    "run_id", "filename", "row_count", "column_count", "columns",
}


def validate_dm_004(obj: Dict[str, Any]) -> List[str]:
    violations: List[str] = []
    if not isinstance(obj, dict):
        return ["DM-004: expected dict"]
    for k in DM_004_REQUIRED:
        if k not in obj:
            violations.append(f"DM-004: missing '{k}'")
    cols = obj.get("columns", [])
    if not isinstance(cols, list):
        violations.append("DM-004: columns must be a list")
    else:
        for i, c in enumerate(cols):
            if not isinstance(c, dict):
                violations.append(f"DM-004.columns[{i}]: expected dict")
                continue
            for req in ("name", "dtype", "n_missing", "n_unique"):
                if req not in c:
                    violations.append(f"DM-004.columns[{i}]: missing '{req}'")
    return violations


# ---------------------------------------------------------------------------
# DM-005 — Feature proposal batch
# ---------------------------------------------------------------------------

DM_005_REQUIRED_PROPOSAL = {
    "proposed_name", "description", "source_columns",
    "transformation_method", "benchmark_comparison",
}


def validate_dm_005(obj: Dict[str, Any]) -> List[str]:
    violations: List[str] = []
    if not isinstance(obj, dict):
        return ["DM-005: expected dict"]
    for k in ("batch_number", "batch_type", "proposed_features"):
        if k not in obj:
            violations.append(f"DM-005: missing '{k}'")
    bt = obj.get("batch_type")
    if bt and bt not in BATCH_TYPES:
        violations.append(f"DM-005: unknown batch_type '{bt}'")
    features = obj.get("proposed_features", [])
    if not isinstance(features, list):
        violations.append("DM-005: proposed_features must be a list")
    else:
        for i, f in enumerate(features):
            if not isinstance(f, dict):
                violations.append(f"DM-005.proposed_features[{i}]: expected dict")
                continue
            for req in DM_005_REQUIRED_PROPOSAL:
                if req not in f:
                    violations.append(f"DM-005[{i}]: missing '{req}'")
    return violations


# ---------------------------------------------------------------------------
# DM-006 — Persona challenge response
# ---------------------------------------------------------------------------

def validate_dm_006(obj: Dict[str, Any]) -> List[str]:
    violations: List[str] = []
    if not isinstance(obj, dict):
        return ["DM-006: expected dict"]
    for k in ("persona", "batch_number", "reviews"):
        if k not in obj:
            violations.append(f"DM-006: missing '{k}'")
    p = obj.get("persona")
    if p and p not in PERSONA_TYPES:
        violations.append(f"DM-006: unknown persona '{p}'")
    reviews = obj.get("reviews", [])
    if not isinstance(reviews, list):
        violations.append("DM-006: reviews must be a list")
    else:
        for i, r in enumerate(reviews):
            if not isinstance(r, dict):
                violations.append(f"DM-006.reviews[{i}]: expected dict")
                continue
            for req in ("proposed_name", "approved", "recommendation"):
                if req not in r:
                    violations.append(f"DM-006[{i}]: missing '{req}'")
    return violations


# ---------------------------------------------------------------------------
# DM-007 — Approved feature set
# ---------------------------------------------------------------------------

DM_007_REQUIRED = {
    "feature_name", "proposed_name", "batch_number", "batch_type",
    "description", "source_columns", "transformation_method",
    "confidence_score", "confidence_band",
}


def validate_dm_007_entry(obj: Dict[str, Any], idx: int = 0) -> List[str]:
    violations: List[str] = []
    if not isinstance(obj, dict):
        return [f"DM-007[{idx}]: expected dict"]
    for k in DM_007_REQUIRED:
        if k not in obj:
            violations.append(f"DM-007[{idx}]: missing '{k}'")
    score = obj.get("confidence_score")
    if score not in CONFIDENCE_SCORES:
        violations.append(
            f"DM-007[{idx}]: score must be in {sorted(CONFIDENCE_SCORES)}, got {score}"
        )
    name = obj.get("feature_name", "")
    if isinstance(name, str) and not name.startswith("feat_"):
        violations.append(f"DM-007[{idx}]: feature_name must start with 'feat_'")
    return violations


# ---------------------------------------------------------------------------
# DM-008 — Verification result
# ---------------------------------------------------------------------------

def validate_dm_008(obj: Dict[str, Any]) -> List[str]:
    violations: List[str] = []
    if not isinstance(obj, dict):
        return ["DM-008: expected dict"]
    for k in ("run_id", "verification_status", "checks"):
        if k not in obj:
            violations.append(f"DM-008: missing '{k}'")
    status = obj.get("verification_status")
    if status not in ("pass", "corrections_applied", "issues_found"):
        violations.append(f"DM-008: unknown status '{status}'")
    checks = obj.get("checks", [])
    if not isinstance(checks, list):
        violations.append("DM-008: checks must be a list")
    return violations


if __name__ == "__main__":
    # Quick smoke
    vr = {
        "run_id": "feature-20260414-000000-abcd",
        "filename": "test.csv",
        "file_path": "/tmp/test.csv",
        "row_count": 100,
        "column_count": 5,
        "cell_count": 500,
        "column_names": ["a", "b", "c", "d", "e"],
        "column_dtypes": {"a": "int64"},
        "has_metadata_json": False,
        "has_transformation_report": False,
        "metadata_provenance_valid": False,
        "pii_flags": [],
        "warnings": [],
        "validated_at": "2026-04-14T00:00:00",
    }
    print("DM-003:", validate_dm_003(vr))

    ds = {
        "run_id": "feature-20260414-000000-abcd",
        "filename": "test.csv",
        "row_count": 100,
        "column_count": 2,
        "columns": [
            {"name": "a", "dtype": "int64", "n_missing": 0, "n_unique": 100,
             "is_unique": True, "sample_values": [1, 2, 3], "stats": {},
             "pii_flag": None},
        ],
    }
    print("DM-004:", validate_dm_004(ds))

"""Data schemas for Feature 1 (Data Profiling).

Covers DM-001 through DM-010 as typed dict templates with validation helpers.
Each schema has a ``validate_{name}`` function that returns a list of
violations (strings) rather than raising — this lets callers accumulate
errors across multiple checks before deciding whether to halt.

Reference: ``specs/002-imputation-feature-1/data-model.md``
"""
from __future__ import annotations

from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# DM-002 — Validation Result
# ---------------------------------------------------------------------------

DM_002_REQUIRED_KEYS = {
    "run_id": str,
    "filename": str,
    "file_path": str,
    "row_count": int,
    "column_count": int,
    "cell_count": int,
    "is_single_row": bool,
    "warnings": list,
    "validated_at": str,
}


def validate_dm_002(obj: Dict[str, Any]) -> List[str]:
    """Validate a ``validation_result`` dict against DM-002."""
    violations: List[str] = []
    if not isinstance(obj, dict):
        return [f"DM-002: expected dict, got {type(obj).__name__}"]
    for key, expected_type in DM_002_REQUIRED_KEYS.items():
        if key not in obj:
            violations.append(f"DM-002: missing required key '{key}'")
            continue
        if not isinstance(obj[key], expected_type):
            violations.append(
                f"DM-002: key '{key}' should be "
                f"{expected_type.__name__}, got {type(obj[key]).__name__}"
            )
    if "run_id" in obj and isinstance(obj["run_id"], str):
        if not obj["run_id"].startswith("profile-"):
            violations.append("DM-002: run_id must start with 'profile-'")
    if "cell_count" in obj and "row_count" in obj and "column_count" in obj:
        try:
            if obj["cell_count"] != obj["row_count"] * obj["column_count"]:
                violations.append(
                    "DM-002: cell_count must equal row_count × column_count"
                )
        except TypeError:
            pass  # already reported as type violations above
    return violations


# ---------------------------------------------------------------------------
# DM-003 — Data Quality Detections
# ---------------------------------------------------------------------------

DM_003_CHECK_NAMES = {
    "duplicate_column_names",
    "special_characters",
    "all_missing_columns",
    "mixed_types",
}

DM_003_STATUS_VALUES = {"found", "clean"}


def validate_dm_003(items: List[Dict[str, Any]]) -> List[str]:
    """Validate a ``quality_detections`` list against DM-003."""
    violations: List[str] = []
    if not isinstance(items, list):
        return [f"DM-003: expected list, got {type(items).__name__}"]
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            violations.append(f"DM-003[{i}]: expected dict")
            continue
        for key in ("check", "status", "affected_columns", "details"):
            if key not in item:
                violations.append(f"DM-003[{i}]: missing key '{key}'")
        if item.get("check") not in DM_003_CHECK_NAMES:
            violations.append(
                f"DM-003[{i}]: check '{item.get('check')}' not in "
                f"{sorted(DM_003_CHECK_NAMES)}"
            )
        if item.get("status") not in DM_003_STATUS_VALUES:
            violations.append(
                f"DM-003[{i}]: status '{item.get('status')}' not in "
                f"{sorted(DM_003_STATUS_VALUES)}"
            )
        if not isinstance(item.get("affected_columns", []), list):
            violations.append(f"DM-003[{i}]: affected_columns must be a list")
        if not isinstance(item.get("details", ""), str):
            violations.append(f"DM-003[{i}]: details must be a string")
    return violations


# ---------------------------------------------------------------------------
# DM-004 — PII Scan Results
# ---------------------------------------------------------------------------

DM_004_PII_TYPES = {
    "direct_name",
    "direct_contact",
    "direct_identifier",
    "indirect",
    "financial",
}

DM_004_DETECTION_SOURCES = {"column_name_pattern", "value_pattern_llm"}
DM_004_CONFIDENCE_VALUES = {"high", "medium"}


def validate_dm_004(items: List[Dict[str, Any]]) -> List[str]:
    """Validate a ``pii_scan`` list against DM-004."""
    violations: List[str] = []
    if not isinstance(items, list):
        return [f"DM-004: expected list, got {type(items).__name__}"]
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            violations.append(f"DM-004[{i}]: expected dict")
            continue
        for key in ("column_name", "pii_type", "pii_category",
                    "detection_source", "confidence"):
            if key not in item:
                violations.append(f"DM-004[{i}]: missing key '{key}'")
        if item.get("pii_type") not in DM_004_PII_TYPES:
            violations.append(
                f"DM-004[{i}]: pii_type '{item.get('pii_type')}' not in "
                f"{sorted(DM_004_PII_TYPES)}"
            )
        if item.get("detection_source") not in DM_004_DETECTION_SOURCES:
            violations.append(
                f"DM-004[{i}]: detection_source "
                f"'{item.get('detection_source')}' not in "
                f"{sorted(DM_004_DETECTION_SOURCES)}"
            )
        if item.get("confidence") not in DM_004_CONFIDENCE_VALUES:
            violations.append(
                f"DM-004[{i}]: confidence '{item.get('confidence')}' not in "
                f"{sorted(DM_004_CONFIDENCE_VALUES)}"
            )
    return violations


# ---------------------------------------------------------------------------
# DM-005 — ydata-profiling Configuration (builder, not a schema validator)
# ---------------------------------------------------------------------------

def build_dm_005_config(filename: str, cell_count: int) -> Dict[str, Any]:
    """Build the ydata-profiling config per DM-005 and run-profiling.md.

    Notes
    -----
    - ``sensitive=True`` AND ``samples.head=0, samples.tail=0`` are
      applied together as belt-and-suspenders privacy protection.
    - ``minimal=True`` when cell_count > 50,000.
    """
    return {
        "title": f"Data Profile: {filename}",
        "minimal": cell_count > 50_000,
        "explorative": False,
        "sensitive": True,
        "correlations": {
            "pearson": {"calculate": True},
            "spearman": {"calculate": False},
            "kendall": {"calculate": False},
            "phi_k": {"calculate": False},
        },
        "missing_diagrams": {
            "bar": True,
            "matrix": False,
            "heatmap": False,
        },
        "samples": {
            "head": 0,
            "tail": 0,
        },
    }


# ---------------------------------------------------------------------------
# DM-006 — Profiling Statistics
# ---------------------------------------------------------------------------

DM_006_TOP_LEVEL_KEYS = {"profiling_mode", "dataset", "columns", "correlations"}
DM_006_MODE_VALUES = {"full", "minimal"}


def validate_dm_006(obj: Dict[str, Any]) -> List[str]:
    """Validate a ``profiling_statistics`` dict against DM-006 (structural)."""
    violations: List[str] = []
    if not isinstance(obj, dict):
        return [f"DM-006: expected dict, got {type(obj).__name__}"]
    for key in DM_006_TOP_LEVEL_KEYS:
        if key not in obj:
            violations.append(f"DM-006: missing top-level key '{key}'")
    if obj.get("profiling_mode") not in DM_006_MODE_VALUES:
        violations.append(
            f"DM-006: profiling_mode '{obj.get('profiling_mode')}' not in "
            f"{sorted(DM_006_MODE_VALUES)}"
        )
    if "dataset" in obj and isinstance(obj["dataset"], dict):
        for key in ("n_rows", "n_columns", "n_cells"):
            if key not in obj["dataset"]:
                violations.append(f"DM-006: dataset missing '{key}'")
    if "columns" in obj and not isinstance(obj["columns"], dict):
        violations.append("DM-006: columns must be a dict keyed by column name")
    return violations


# ---------------------------------------------------------------------------
# DM-007 — Chart Metadata
# ---------------------------------------------------------------------------

DM_007_CHART_TYPES = {
    "missing_values",
    "dtype_distribution",
    "numeric_histograms",
}


def validate_dm_007(items: List[Dict[str, Any]]) -> List[str]:
    """Validate a ``chart_metadata`` list against DM-007."""
    violations: List[str] = []
    if not isinstance(items, list):
        return [f"DM-007: expected list, got {type(items).__name__}"]
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            violations.append(f"DM-007[{i}]: expected dict")
            continue
        for key in ("chart_type", "filename", "file_path", "included",
                    "description"):
            if key not in item:
                violations.append(f"DM-007[{i}]: missing key '{key}'")
        if item.get("chart_type") not in DM_007_CHART_TYPES:
            violations.append(
                f"DM-007[{i}]: chart_type '{item.get('chart_type')}' not in "
                f"{sorted(DM_007_CHART_TYPES)}"
            )
        if "included" in item and not isinstance(item["included"], bool):
            violations.append(f"DM-007[{i}]: included must be bool")
    return violations


# ---------------------------------------------------------------------------
# DM-010 — Feature 2 Handoff (JSON output)
# ---------------------------------------------------------------------------

DM_010_TOP_LEVEL_KEYS = {
    "run_id",
    "filename",
    "validated_at",
    "profiling_mode",
    "validation_result",
    "quality_detections",
    "pii_scan",
    "profiling_statistics",
}


def validate_dm_010(obj: Dict[str, Any]) -> List[str]:
    """Validate the JSON handoff structure against DM-010."""
    violations: List[str] = []
    if not isinstance(obj, dict):
        return [f"DM-010: expected dict, got {type(obj).__name__}"]
    for key in DM_010_TOP_LEVEL_KEYS:
        if key not in obj:
            violations.append(f"DM-010: missing top-level key '{key}'")
    # Delegate to nested validators
    if "validation_result" in obj:
        violations.extend(validate_dm_002(obj["validation_result"]))
    if "quality_detections" in obj:
        violations.extend(validate_dm_003(obj["quality_detections"]))
    if "pii_scan" in obj:
        violations.extend(validate_dm_004(obj["pii_scan"]))
    if "profiling_statistics" in obj:
        violations.extend(validate_dm_006(obj["profiling_statistics"]))
    return violations


if __name__ == "__main__":
    # Quick smoke test
    from run_id import generate_run_id

    sample = {
        "run_id": generate_run_id(),
        "filename": "test.csv",
        "file_path": "/tmp/test.csv",
        "row_count": 100,
        "column_count": 5,
        "cell_count": 500,
        "is_single_row": False,
        "warnings": [],
        "validated_at": "2026-04-13T00:00:00",
    }
    print("DM-002 violations:", validate_dm_002(sample))

    config = build_dm_005_config("test.csv", 1000)
    print("DM-005 config minimal flag:", config["minimal"])
    config_big = build_dm_005_config("big.csv", 60_000)
    print("DM-005 config minimal flag (big):", config_big["minimal"])

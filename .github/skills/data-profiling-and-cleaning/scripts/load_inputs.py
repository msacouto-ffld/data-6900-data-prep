"""Stage 10 — Load Feature 1 outputs.

Globs the sandbox for the Feature 1 profiling JSON, loads it plus the
NL report and original raw CSV, validates required keys, and returns
the tuple of objects downstream stages consume.

Contract: ``contracts/load-feature1-outputs.md``
"""
from __future__ import annotations

import datetime
import glob
import json
import os
from typing import Any, Dict, Tuple

import pandas as pd

from run_id import generate_run_id
from schemas_f2 import validate_dm_101


class LoadInputsError(Exception):
    """Raised when Feature 1 outputs are missing or corrupt."""


def _find_profiling_json(search_dir: str) -> str:
    """Find the most recent profile-*-profiling-data.json."""
    pattern = os.path.join(search_dir, "profile-*-profiling-data.json")
    matches = sorted(glob.glob(pattern))
    if not matches:
        raise LoadInputsError(
            "No profiling data found. Please run data profiling first — "
            "upload your CSV and ask for profiling before cleaning can begin."
        )
    if len(matches) > 1:
        # The run ID embeds the timestamp, so sorted() gives chronological order
        return matches[-1]
    return matches[0]


def load_feature1_outputs(
    search_dir: str = ".",
) -> Tuple[Dict[str, Any], str, pd.DataFrame, Dict[str, Any]]:
    """Load Feature 1 outputs from the sandbox.

    Returns
    -------
    profiling_data:
        Parsed DM-101 JSON (required top-level keys validated).
    nl_report:
        Markdown string of the ``{profiling_run_id}-summary.md`` file.
    raw_df:
        The original raw CSV as a DataFrame.
    run_metadata:
        DM-102 dict with the transform run ID and source pointers.

    Raises
    ------
    LoadInputsError
        If any required file is missing or the JSON is corrupt.
    """
    print("🔍 Loading profiling results...")

    # --- Locate and load the profiling JSON ---
    json_path = _find_profiling_json(search_dir)
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            profiling_data = json.load(f)
    except Exception as exc:
        raise LoadInputsError(
            "Profiling data is incomplete or corrupted. "
            "Please re-run data profiling."
        ) from exc

    # Validate required keys against DM-101
    violations = validate_dm_101(profiling_data)
    if violations:
        # Surface only the first couple to keep the error readable
        print(f"   Validation errors: {violations[:3]}")
        raise LoadInputsError(
            "Profiling data is incomplete or corrupted. "
            "Please re-run data profiling."
        )

    profiling_run_id = profiling_data["run_id"]
    print(f"✅ Profiling data loaded: {profiling_run_id}")

    # --- Load the NL report markdown ---
    nl_report_path = os.path.join(
        search_dir, f"{profiling_run_id}-summary.md"
    )
    if not os.path.isfile(nl_report_path):
        raise LoadInputsError(
            "Profiling data is incomplete or corrupted. "
            "Please re-run data profiling."
        )
    try:
        with open(nl_report_path, "r", encoding="utf-8") as f:
            nl_report = f.read()
    except Exception as exc:
        raise LoadInputsError(
            "Profiling data is incomplete or corrupted. "
            "Please re-run data profiling."
        ) from exc

    # --- Load the original raw CSV ---
    raw_csv_path = profiling_data.get("validation_result", {}).get("file_path")
    if not raw_csv_path or not os.path.isfile(raw_csv_path):
        raise LoadInputsError(
            "Original CSV not found in this session. "
            "Please re-upload your CSV and re-run profiling."
        )
    try:
        raw_df = pd.read_csv(raw_csv_path)
    except Exception as exc:
        raise LoadInputsError(
            "Original CSV could not be re-read. "
            "Please re-upload your CSV and re-run profiling."
        ) from exc

    original_filename = profiling_data.get("filename", os.path.basename(raw_csv_path))
    print(
        f"✅ Original CSV loaded: {original_filename} "
        f"({raw_df.shape[0]} rows × {raw_df.shape[1]} columns)"
    )

    # --- Build DM-102 run metadata ---
    transform_run_id = generate_run_id(prefix="transform")
    run_metadata: Dict[str, Any] = {
        "transform_run_id": transform_run_id,
        "source_profiling_run_id": profiling_run_id,
        "original_filename": original_filename,
        "original_file_path": raw_csv_path,
        "started_at": datetime.datetime.now().isoformat(),
        "random_seed": 42,
        "pipeline_version": "1.0",
    }
    print(f"✅ Run ID: {transform_run_id}")
    print()
    print("Ready to analyze and propose transformations.")
    print()

    return profiling_data, nl_report, raw_df, run_metadata


if __name__ == "__main__":
    import sys
    try:
        search = sys.argv[1] if len(sys.argv) > 1 else "."
        profiling_data, nl_report, raw_df, run_metadata = load_feature1_outputs(search)
        print(f"\nLoaded {len(profiling_data)} top-level profiling keys")
        print(f"NL report: {len(nl_report)} chars")
        print(f"Raw DF: {raw_df.shape}")
        print(f"Transform run ID: {run_metadata['transform_run_id']}")
    except LoadInputsError as e:
        print(f"❌ {e}")
        sys.exit(1)

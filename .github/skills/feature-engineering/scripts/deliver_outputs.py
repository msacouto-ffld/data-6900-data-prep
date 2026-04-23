"""Stage 8 — Deliver all Skill B outputs.

Writes:
- {run_id}-engineered.csv (already written by execute_features)
- {run_id}-transformation-report.md
- {run_id}-data-dictionary.md
- {run_id}-mistake-log.md (already written throughout)

Displays report + dictionary inline, then download links.

Contract: contracts/deliver-outputs.md
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional


def deliver_outputs(
    engineered_csv_path: Optional[str],
    report_text: str,
    dictionary_text: str,
    validation_result: Dict[str, Any],
    log_path: str,
    output_dir: str = ".",
    n_original_cols: int = 0,
    n_new_cols: int = 0,
) -> Dict[str, Optional[str]]:
    """Write output files and print download presentation.

    Returns dict of file paths written (or None on failure).
    """
    run_id = validation_result["run_id"]

    report_name = f"{run_id}-transformation-report.md"
    dict_name = f"{run_id}-data-dictionary.md"

    report_path = os.path.join(output_dir, report_name)
    dict_path = os.path.join(output_dir, dict_name)

    written: Dict[str, Optional[str]] = {
        "engineered_csv": engineered_csv_path if engineered_csv_path and os.path.isfile(engineered_csv_path) else None,
        "transformation_report": None,
        "data_dictionary": None,
        "mistake_log": log_path if os.path.isfile(log_path) else None,
    }

    # Write report
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_text)
        written["transformation_report"] = report_path
    except Exception as exc:
        print(
            f"Output error: could not save {report_name}. "
            f"The content has been delivered inline above. ({exc})"
        )

    # Write dictionary
    try:
        with open(dict_path, "w", encoding="utf-8") as f:
            f.write(dictionary_text)
        written["data_dictionary"] = dict_path
    except Exception as exc:
        print(
            f"Output error: could not save {dict_name}. "
            f"The content has been delivered inline above. ({exc})"
        )

    # Inline delivery
    print()
    print(report_text)
    print()
    print(dictionary_text)
    print()

    # Download presentation
    csv_basename = os.path.basename(engineered_csv_path) if engineered_csv_path else f"{run_id}-engineered.csv"
    print("📥 Your feature engineering outputs are ready:")
    print(
        f"   • {csv_basename}\n"
        f"     — Feature-engineered dataset "
        f"({n_original_cols} original + {n_new_cols} new columns)"
    )
    if written["transformation_report"]:
        print(
            f"   • {report_name}\n"
            "     — Full transformation report with all feature details"
        )
    if written["data_dictionary"]:
        print(
            f"   • {dict_name}\n"
            "     — Data dictionary for all engineered features"
        )
    print()
    print(
        "Engineered columns are prefixed with 'feat_' — use\n"
        "df.filter(like='feat_') to select them."
    )
    print()
    log_basename = os.path.basename(log_path) if log_path else f"{run_id}-mistake-log.md"
    print(f"📋 Mistake log for this run:\n   • {log_basename}")

    return written


if __name__ == "__main__":
    print("deliver_outputs is invoked by the orchestrator.")

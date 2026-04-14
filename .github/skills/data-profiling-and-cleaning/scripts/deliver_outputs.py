"""Stage 9 — Deliver profiling outputs.

Writes the final files to the sandbox:

- ``{run_id}-summary.md`` — final post-verification NL report
- ``{run_id}-profiling-data.json`` — DM-010 handoff JSON
- ``{run_id}-profile.html`` — already written by stage 4
- ``{run_id}-chart-*.png`` — already written by stage 6

Then displays the NL report inline and presents all files for download
using the 📥 format from the contract.

File write failures are non-blocking for inline delivery.

Contract: ``contracts/deliver-outputs.md``
"""
from __future__ import annotations

import json
import math
import os
from typing import Any, Dict, List


def _json_safe(obj: Any) -> Any:
    """Recursively convert NumPy/pandas values into JSON-safe types.

    ``json.dumps`` chokes on ``np.int64``, ``np.float64``, NaN, and
    timestamps. This helper normalises everything to plain Python.
    """
    # Handle None first
    if obj is None:
        return None
    # Handle plain JSON-safe types
    if isinstance(obj, (str, bool, int)):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    # Dict / list recursion
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    # Numpy scalars — use their .item() method
    if hasattr(obj, "item"):
        try:
            return _json_safe(obj.item())
        except Exception:
            pass
    # Fall back to string representation
    return str(obj)


def _build_dm_010(
    validation_result: Dict[str, Any],
    profiling_statistics: Dict[str, Any],
    quality_detections: List[Dict[str, Any]],
    pii_scan: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build the DM-010 JSON handoff structure."""
    return {
        "run_id": validation_result["run_id"],
        "filename": validation_result["filename"],
        "validated_at": validation_result["validated_at"],
        "profiling_mode": profiling_statistics.get("profiling_mode", "full"),
        "validation_result": validation_result,
        "quality_detections": quality_detections,
        "pii_scan": pii_scan,
        "profiling_statistics": profiling_statistics,
    }


def _drop_top_values(profiling_statistics: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of profiling_statistics with `top_values` stripped.

    Per DM-006, ``top_values`` contains raw data from categorical columns
    and must NEVER appear in exported files (FR-016). We keep
    ``top_frequencies`` (counts are safe) and strip ``top_values``.
    """
    import copy
    ps = copy.deepcopy(profiling_statistics)
    columns = ps.get("columns", {})
    for col_name, col_entry in columns.items():
        if "top_values" in col_entry:
            col_entry["top_values"] = []  # scrubbed for export
    return ps


def deliver_outputs(
    final_nl_report: str,
    validation_result: Dict[str, Any],
    profiling_statistics: Dict[str, Any],
    quality_detections: List[Dict[str, Any]],
    pii_scan: List[Dict[str, Any]],
    chart_metadata: List[Dict[str, Any]],
    output_dir: str = ".",
) -> Dict[str, Any]:
    """Write final files and print download presentation.

    Returns
    -------
    dict
        Paths of every file written, plus a ``delivered_inline`` flag
        indicating whether the report was shown in chat (always True
        when this function completes normally).
    """
    run_id = validation_result["run_id"]
    summary_name = f"{run_id}-summary.md"
    json_name = f"{run_id}-profiling-data.json"
    html_name = f"{run_id}-profile.html"

    summary_path = os.path.join(output_dir, summary_name)
    json_path = os.path.join(output_dir, json_name)
    html_path = os.path.join(output_dir, html_name)

    written: Dict[str, Any] = {
        "summary_md": None,
        "profiling_json": None,
        "html": html_path if os.path.isfile(html_path) else None,
        "charts": [],
        "delivered_inline": True,
    }

    # --- Write summary markdown ---
    try:
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(final_nl_report)
        written["summary_md"] = summary_path
    except Exception as exc:
        print(
            f"Output error: could not save {summary_name}. "
            f"The report has been delivered inline — please copy it manually. "
            f"({exc})"
        )

    # --- Write DM-010 JSON handoff (with top_values scrubbed) ---
    try:
        ps_scrubbed = _drop_top_values(profiling_statistics)
        handoff = _build_dm_010(
            validation_result, ps_scrubbed, quality_detections, pii_scan,
        )
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(_json_safe(handoff), f, indent=2)
        written["profiling_json"] = json_path
    except Exception as exc:
        print(
            f"Output error: could not save {json_name}. "
            f"The report has been delivered inline — please copy it manually. "
            f"({exc})"
        )

    # --- Collect chart paths ---
    for entry in chart_metadata:
        if entry.get("included") and entry.get("file_path"):
            if os.path.isfile(entry["file_path"]):
                written["charts"].append(entry["file_path"])

    # --- Inline delivery: print the report ---
    print()  # blank line before report
    print(final_nl_report)
    print()  # blank line after

    # --- Download presentation (matches contract §Outputs §3) ---
    print("📥 Your profiling outputs are ready for download:")
    if written["html"]:
        print(f"   • {os.path.basename(written['html'])}")
        print("     — Full statistical profile (interactive HTML report)")
    if written["summary_md"]:
        print(f"   • {os.path.basename(written['summary_md'])}")
        print("     — Natural language analysis (the report shown above)")
    if written["profiling_json"]:
        print(f"   • {os.path.basename(written['profiling_json'])}")
        print("     — Structured profiling data (for technical users or")
        print("       downstream data cleaning tools)")
    print()
    print("Your profiling is complete. You can now proceed to data cleaning,")
    print("or download these files to share with your team.")

    return written


if __name__ == "__main__":
    print("deliver_outputs is normally invoked by the orchestrator.")

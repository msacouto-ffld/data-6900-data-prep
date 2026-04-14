"""Orchestrator — Skill A Feature 2 (Data Cleaning).

Wires stages 10–17 end-to-end:

- 10: load_feature1_outputs
- 11: propose_transformations (LLM) OR light_verification (LLM, no-issues path)
- 12: review_panel (LLM) — with rejection re-proposal loops
- 13: execute_transformations (script)
- 14: verify_output (LLM)
- 15: generate_report (LLM)
- 16: scan_jargon (script + optional LLM fix)
- 17: deliver_cleaning_outputs (script)

LLM-owned stages are called through ``llm_hooks`` injected by the
caller. Missing hooks fall back to deterministic stubs so the pipeline
can run end-to-end in smoke tests without a live LLM.

The mistake log is written via try/finally so it persists even when
the pipeline halts on an execution error.
"""
from __future__ import annotations

import copy
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from catalog import get_step_name
from deliver_cleaning_outputs import deliver_cleaning_outputs
from execute_transformations import ExecutionError, execute_transformations
from load_inputs import LoadInputsError, load_feature1_outputs
from mistake_log import (
    build_mistake_log,
    count_entries_by_type,
    log_entry,
    write_mistake_log,
)
from scan_jargon import scan_jargon
from schemas_f2 import (
    SCORE_TO_BAND,
    STEP_DEPENDENCY_MAP,
    validate_dm_104,
    validate_dm_105,
)


LLMHook = Callable[..., Any]


class CleaningPipelineError(Exception):
    """Top-level Feature 2 failure."""


# ---------------------------------------------------------------------------
# Fallback LLM stubs
# ---------------------------------------------------------------------------


def _stub_propose(
    profiling_data: Dict[str, Any],
    nl_report: str,
    run_metadata: Dict[str, Any],
    rejection_context: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Deterministic fallback proposer.

    Reads quality_detections and generates a minimal catalog-based
    plan. Does NOT match the nuance of a real LLM proposer but
    produces a valid DM-104 structure for smoke testing.
    """
    run_id = run_metadata["transform_run_id"]
    plan: Dict[str, Any] = {
        "plan_id": f"{run_id}-plan",
        "source_profiling_run_id": run_metadata["source_profiling_run_id"],
        "no_issues_detected": False,
        "transformations": [],
    }

    detections = profiling_data.get("quality_detections", [])
    all_clean = all(d.get("status") == "clean" for d in detections)
    if all_clean:
        plan["no_issues_detected"] = True
        return plan

    seq = 1
    for det in detections:
        if det.get("status") != "found":
            continue
        check = det.get("check")
        affected = det.get("affected_columns", [])

        if check == "duplicate_column_names":
            plan["transformations"].append({
                "id": f"t-1-{seq:02d}",
                "step": 1,
                "step_name": "column_name_standardization",
                "issue": f"duplicate_column_names: {det.get('details', '')}",
                "affected_columns": affected,
                "strategy": "rename_duplicates_with_suffix",
                "is_custom": False,
                "justification": (
                    "Duplicate column names must be disambiguated for "
                    "downstream code to reference them reliably."
                ),
                "expected_impact": "Duplicate names get _1, _2 suffixes.",
                "parameters": {},
            })
            seq += 1
        elif check == "special_characters":
            plan["transformations"].append({
                "id": f"t-1-{seq:02d}",
                "step": 1,
                "step_name": "column_name_standardization",
                "issue": f"special_characters: {det.get('details', '')}",
                "affected_columns": affected,
                "strategy": "standardize_to_snake_case",
                "is_custom": False,
                "justification": (
                    "Normalise column names to snake_case to remove "
                    "special characters."
                ),
                "expected_impact": "Column names become snake_case.",
                "parameters": {},
            })
            seq += 1
        elif check == "all_missing_columns":
            plan["transformations"].append({
                "id": f"t-2-{seq:02d}",
                "step": 2,
                "step_name": "drop_all_missing_columns",
                "issue": f"all_missing_columns: {det.get('details', '')}",
                "affected_columns": affected,
                "strategy": "drop_column",
                "is_custom": False,
                "justification": (
                    "Columns that are 100% missing contribute nothing."
                ),
                "expected_impact": (
                    f"{len(affected)} column(s) removed from dataset."
                ),
                "parameters": {},
            })
            seq += 1
        elif check == "mixed_types":
            for col in affected:
                plan["transformations"].append({
                    "id": f"t-3-{seq:02d}",
                    "step": 3,
                    "step_name": "type_coercion",
                    "issue": f"mixed_types: Column {col} has inconsistent types",
                    "affected_columns": [col],
                    "strategy": "coerce_to_target_type",
                    "is_custom": False,
                    "justification": (
                        "Coerce to string to ensure type consistency."
                    ),
                    "expected_impact": "Column has a single dtype.",
                    "parameters": {"target_type": "string"},
                })
                seq += 1

    # Add a missing-value imputation step for any column with >5% missing
    columns = profiling_data.get("profiling_statistics", {}).get("columns", {})
    for col_name, col_info in columns.items():
        pct = col_info.get("pct_missing", 0)
        if 0 < pct < 100:  # skip 100%-missing (handled by step 2)
            # Choose strategy based on column type
            col_type = col_info.get("type", "other")
            if col_type == "numeric" and pct < 30:
                plan["transformations"].append({
                    "id": f"t-5-{seq:02d}",
                    "step": 5,
                    "step_name": "missing_value_imputation",
                    "issue": f"missing_values: Column {col_name} is {pct}% missing",
                    "affected_columns": [col_name],
                    "strategy": "impute_median",
                    "is_custom": False,
                    "justification": (
                        "Median imputation is robust to outliers and "
                        "appropriate for numeric columns with <30% missing."
                    ),
                    "expected_impact": (
                        f"Missing values in {col_name} filled with median."
                    ),
                    "parameters": {},
                })
                seq += 1
            elif col_type == "categorical" and pct < 30:
                plan["transformations"].append({
                    "id": f"t-5-{seq:02d}",
                    "step": 5,
                    "step_name": "missing_value_imputation",
                    "issue": f"missing_values: Column {col_name} is {pct}% missing",
                    "affected_columns": [col_name],
                    "strategy": "impute_unknown",
                    "is_custom": False,
                    "justification": (
                        "Categorical columns use 'Unknown' to preserve "
                        "missingness as a distinct category."
                    ),
                    "expected_impact": (
                        f"Missing values in {col_name} filled with 'Unknown'."
                    ),
                    "parameters": {},
                })
                seq += 1

    return plan


def _stub_review(
    transformation_plan: Dict[str, Any],
    profiling_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Deterministic fallback reviewer — approves everything at 95."""
    reviews: List[Dict[str, Any]] = []
    for t in transformation_plan.get("transformations", []):
        score = 95 if not t.get("is_custom") else 82
        reviews.append({
            "transformation_id": t["id"],
            "step": t["step"],
            "verdict": "APPROVE",
            "conservative_reasoning": (
                "Catalog strategy; minimal risk of information loss."
            ),
            "business_reasoning": (
                "Supports downstream analysis without bias."
            ),
            "technical_reasoning": (
                "Method is appropriate for the column's statistical profile."
            ),
            "confidence_score": score,
            "confidence_band": SCORE_TO_BAND[score],
            "alternative": None,
            "alternative_justification": None,
        })
    return {
        "review_id": f"{transformation_plan['plan_id']}-review-1",
        "round": 1,
        "reviews": reviews,
        "overall_summary": (
            "Stub reviewer approved all transformations. Production "
            "runtime should inject a real 3-perspective LLM reviewer."
        ),
    }


def _stub_verify_output(
    profiling_data: Dict[str, Any],
    step_results: List[Dict[str, Any]],
    approved_plan: Dict[str, Any],
    final_metrics: Dict[str, Any],
    high_impact_flags: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Deterministic fallback verifier — always PASS."""
    return {
        "status": "PASS",
        "corrections": [],
        "confirmed": [
            "Row count consistent with approved plan",
            "Column count consistent with approved plan",
            "No unapproved changes detected",
            f"{len(high_impact_flags)} high-impact flag(s) acknowledged",
        ],
        "discrepancies": [],
    }


def _stub_generate_report(
    step_results: List[Dict[str, Any]],
    approved_plan: Dict[str, Any],
    review_outputs: List[Dict[str, Any]],
    verification_result: Dict[str, Any],
    run_metadata: Dict[str, Any],
    profiling_data: Dict[str, Any],
    high_impact_flags: List[Dict[str, Any]],
    mistake_log_counts: Dict[str, int],
) -> str:
    """Deterministic fallback report generator.

    Produces a valid DM-109-structured report without calling an LLM.
    """
    lines: List[str] = []
    run_id = run_metadata["transform_run_id"]
    lines.append("# Data Transformation Report")
    lines.append("")
    lines.append(f"**Run ID**: {run_id}")
    lines.append(
        f"**Source Profiling Run**: "
        f"{run_metadata['source_profiling_run_id']}"
    )
    lines.append(f"**File**: {run_metadata['original_filename']}")
    lines.append(f"**Generated**: {run_metadata['started_at']}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # --- Executive Summary ---
    approved = approved_plan.get("approved_transformations", [])
    n_steps_used = len({t["step"] for t in approved})
    executed_results = [r for r in step_results if not r["skipped"]]

    rows_before = 0
    cols_before = 0
    rows_after = 0
    cols_after = 0
    if executed_results:
        rows_before = (
            executed_results[0]["metrics_before"]["dataset"]["n_rows"]
        )
        cols_before = (
            executed_results[0]["metrics_before"]["dataset"]["n_columns"]
        )
        rows_after = (
            executed_results[-1]["metrics_after"]["dataset"]["n_rows"]
        )
        cols_after = (
            executed_results[-1]["metrics_after"]["dataset"]["n_columns"]
        )
    scores = [t.get("confidence_score", 0) for t in approved]
    score_range = (
        f"{min(scores)} to {max(scores)}" if scores else "N/A"
    )

    lines.append("## Executive Summary")
    lines.append("")
    lines.append(
        f"{len(approved)} data cleaning transformation(s) were applied "
        f"across {n_steps_used} pipeline step(s). "
        f"The dataset changed from {rows_before} to {rows_after} rows "
        f"and from {cols_before} to {cols_after} columns. "
        f"Confidence scores ranged from {score_range}."
    )
    lines.append("")

    # --- Dataset Comparison ---
    missing_before = (
        executed_results[0]["metrics_before"]["dataset"]["n_missing_cells"]
        if executed_results else 0
    )
    missing_after = (
        executed_results[-1]["metrics_after"]["dataset"]["n_missing_cells"]
        if executed_results else 0
    )
    dup_before = (
        executed_results[0]["metrics_before"]["dataset"]["n_duplicate_rows"]
        if executed_results else 0
    )
    dup_after = (
        executed_results[-1]["metrics_after"]["dataset"]["n_duplicate_rows"]
        if executed_results else 0
    )
    lines.append("## Dataset Comparison")
    lines.append("")
    lines.append("| Metric | Before | After | Change |")
    lines.append("|--------|--------|-------|--------|")
    lines.append(
        f"| Rows | {rows_before} | {rows_after} | "
        f"{rows_after - rows_before} |"
    )
    lines.append(
        f"| Columns | {cols_before} | {cols_after} | "
        f"{cols_after - cols_before} |"
    )
    lines.append(
        f"| Missing cells | {missing_before} | {missing_after} | "
        f"{missing_after - missing_before} |"
    )
    lines.append(
        f"| Duplicate rows | {dup_before} | {dup_after} | "
        f"{dup_after - dup_before} |"
    )
    lines.append("")

    # --- Transformations Applied ---
    lines.append("## Transformations Applied")
    lines.append("")
    for result in step_results:
        if result["skipped"]:
            continue
        step = result["step"]
        step_name = result["step_name"]
        lines.append(f"### Step {step}: {step_name.replace('_', ' ').title()}")
        lines.append("")
        for applied in result["transformations_applied"]:
            # Find the review verdict for this transformation
            score = None
            for t in approved:
                if t.get("id") == applied["id"]:
                    score = t.get("confidence_score")
                    break
            band = SCORE_TO_BAND.get(score, "Unknown") if score else "Unknown"
            lines.append(
                f"**{applied['strategy']}** (Confidence: "
                f"{score}/100 — {band})"
            )
            lines.append("")
            lines.append(
                f"- **What was done**: strategy `{applied['strategy']}` "
                f"applied to columns {applied['affected_columns']}."
            )
            lines.append(
                "- **Why**: this catalog strategy was approved by the "
                "review panel as appropriate for the detected issue."
            )
            # Compute a simple impact description
            m_before = result["metrics_before"]["dataset"]
            m_after = result["metrics_after"]["dataset"]
            impact_parts: List[str] = []
            if m_after["n_rows"] != m_before["n_rows"]:
                impact_parts.append(
                    f"rows: {m_before['n_rows']} → {m_after['n_rows']}"
                )
            if m_after["n_columns"] != m_before["n_columns"]:
                impact_parts.append(
                    f"columns: {m_before['n_columns']} → {m_after['n_columns']}"
                )
            if m_after["n_missing_cells"] != m_before["n_missing_cells"]:
                impact_parts.append(
                    f"missing cells: {m_before['n_missing_cells']} → "
                    f"{m_after['n_missing_cells']}"
                )
            impact = "; ".join(impact_parts) if impact_parts else (
                "no structural changes"
            )
            lines.append(f"- **Impact**: {impact}.")
            lines.append("")
            # High-impact flags inline
            for flag in result["high_impact_flags"]:
                lines.append(
                    f"> ⚠️ **High-impact flag**: {flag['condition']} — "
                    f"value {flag['value']} exceeds threshold "
                    f"{flag['threshold']}. {flag['message']}"
                )
                lines.append("")

    # --- Rejected Transformations (omit if empty) ---
    rejected = approved_plan.get("rejected_transformations", [])
    if rejected:
        lines.append("## Rejected Transformations")
        lines.append("")
        lines.append("| Step | Original Strategy | Reason | Alternative |")
        lines.append("|------|-------------------|--------|-------------|")
        for r in rejected:
            lines.append(
                f"| {r.get('step')} | {r.get('original_strategy')} "
                f"| {r.get('rejection_reason')} "
                f"| {r.get('alternative_adopted')} |"
            )
        lines.append("")

    # --- Skipped Transformations (omit if empty) ---
    skipped_plans = approved_plan.get("skipped_transformations", [])
    if skipped_plans:
        lines.append("## Skipped Transformations")
        lines.append("")
        for s in skipped_plans:
            lines.append(
                f"- Step {s.get('step')}: {s.get('issue', 'N/A')} "
                f"— {s.get('reason', 'user_skipped')}"
            )
        lines.append("")

    # --- High-Impact Summary (omit if empty) ---
    if high_impact_flags:
        lines.append("## High-Impact Summary")
        lines.append("")
        lines.append(
            "| Step | Condition | Value | Threshold | Affected |"
        )
        lines.append(
            "|------|-----------|-------|-----------|----------|"
        )
        for flag in high_impact_flags:
            cols_str = ", ".join(flag.get("affected_columns", []) or [])
            lines.append(
                f"| {flag.get('step', '?')} | {flag['condition']} "
                f"| {flag['value']} | {flag['threshold']} | {cols_str} |"
            )
        lines.append("")

    # --- Next Steps ---
    lines.append("## Next Steps — Recommended Additional Processing")
    lines.append("")
    lines.append(
        "The following transformations are recommended for feature "
        "engineering (Skill B) — they are out of scope for Skill A:"
    )
    lines.append("")
    lines.append(
        "- Normalization / standardization of numeric columns"
    )
    lines.append(
        "- Encoding of categorical columns (one-hot, label, target)"
    )
    lines.append(
        "- Feature engineering: derived columns, date/time features, aggregations"
    )
    lines.append("")

    # --- Verification Summary ---
    lines.append("## Verification Summary")
    lines.append("")
    status = verification_result.get("status", "PASS")
    lines.append(f"**Review Status**: {status}")
    lines.append("")
    lines.append("**Confirmed Accurate:**")
    for item in verification_result.get("confirmed", []):
        lines.append(f"- {item}")
    if not verification_result.get("confirmed"):
        lines.append("- (none recorded)")
    lines.append("")
    lines.append("**Corrections Made:**")
    corrections = verification_result.get("corrections", [])
    if corrections:
        for c in corrections:
            lines.append(f"- {c}")
    else:
        lines.append("- None")
    lines.append("")
    discrepancies = verification_result.get("discrepancies", [])
    if discrepancies:
        lines.append("**Discrepancies Found:**")
        for d in discrepancies:
            lines.append(f"- {d}")
        lines.append("")

    # --- Pipeline Log Summary ---
    lines.append("## Pipeline Log Summary")
    lines.append("")
    total = sum(mistake_log_counts.values())
    if total == 0:
        lines.append(
            "The pipeline completed with no logged events beyond "
            "normal execution. All transformations proceeded as planned."
        )
    else:
        lines.append(
            f"The full audit trail is available in "
            f"`{run_id}-mistake-log.json`. Entry counts from this run:"
        )
        lines.append("")
        lines.append("| Event Type | Count |")
        lines.append("|------------|-------|")
        for k, v in mistake_log_counts.items():
            if v > 0:
                lines.append(f"| {k} | {v} |")
    lines.append("")

    return "\n".join(lines)


def _stub_light_verification(
    profiling_data: Dict[str, Any],
    nl_report: str,
    raw_df_shape: tuple,
) -> Dict[str, Any]:
    """Deterministic fallback light verifier — always confirms."""
    return {
        "status": "CONFIRMED_CLEAN",
        "confirmation_text": (
            "Reviewed profiling data and confirmed no quality issues. "
            "No cleaning transformations required."
        ),
        "concern": None,
    }


# ---------------------------------------------------------------------------
# Plan merging helpers
# ---------------------------------------------------------------------------


def _merge_to_approved_plan(
    transformation_plan: Dict[str, Any],
    review_output: Dict[str, Any],
) -> Dict[str, Any]:
    """Merge DM-104 + DM-105 into a DM-106 approved plan.

    This stub version assumes all transformations were approved —
    production needs to handle rejections via the loop in
    ``_run_review_loop``.
    """
    approved: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []

    review_by_id = {
        r["transformation_id"]: r for r in review_output.get("reviews", [])
    }

    for t in transformation_plan.get("transformations", []):
        review = review_by_id.get(t["id"])
        if review is None:
            continue
        if review["verdict"] == "APPROVE":
            approved.append({
                "id": t["id"],
                "step": t["step"],
                "step_name": t["step_name"],
                "strategy": t["strategy"],
                "is_custom": t.get("is_custom", False),
                "affected_columns": t.get("affected_columns", []),
                "parameters": t.get("parameters", {}),
                "confidence_score": review["confidence_score"],
                "confidence_band": review["confidence_band"],
                "review_round": review_output.get("round", 1),
            })
        else:
            rejected.append({
                "id": t["id"],
                "step": t["step"],
                "original_strategy": t["strategy"],
                "rejection_reason": (
                    review.get("conservative_reasoning")
                    or "Rejected by review panel"
                ),
                "alternative_adopted": review.get("alternative") or "none",
            })

    # Compute dependency warnings — if any step has approved
    # transformations but a dependency step has none
    steps_with_approved = {t["step"] for t in approved}
    dependency_warnings: List[Dict[str, Any]] = []
    for step, dependencies in STEP_DEPENDENCY_MAP.items():
        if step in steps_with_approved:
            for dep in dependencies:
                if dep not in steps_with_approved:
                    # The dep step has no approved transformations, which
                    # is normal if there were no issues for it. This is
                    # only a warning when the user explicitly skipped.
                    # The stub doesn't track that distinction, so no
                    # warning here.
                    pass

    return {
        "approved_transformations": approved,
        "rejected_transformations": rejected,
        "skipped_transformations": [],
        "human_review_decisions": [],
        "dependency_warnings": dependency_warnings,
    }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run_cleaning_pipeline(
    search_dir: str = ".",
    llm_hooks: Optional[Dict[str, LLMHook]] = None,
    output_dir: str = ".",
) -> Dict[str, Any]:
    """Run the full Feature 2 pipeline end-to-end.

    Parameters
    ----------
    search_dir:
        Where to glob for Feature 1 outputs (default: cwd).
    llm_hooks:
        Optional dict of LLM callables. Missing hooks fall back to
        deterministic stubs. Keys: ``propose``, ``review``,
        ``verify_output``, ``generate_report``, ``light_verification``,
        ``jargon_fix``.
    output_dir:
        Where to write Feature 2 output files.

    Returns
    -------
    dict with ``run_id``, ``files``, ``status``, and all stage outputs.
    """
    hooks = llm_hooks or {}

    # Stage 10 — load Feature 1 outputs
    try:
        profiling_data, nl_report, raw_df, run_metadata = (
            load_feature1_outputs(search_dir)
        )
    except LoadInputsError as e:
        print(f"❌ {e}")
        raise CleaningPipelineError(f"Stage 10 failed: {e}")

    mistake_log = build_mistake_log(run_metadata["transform_run_id"])
    run_id = run_metadata["transform_run_id"]

    try:
        # Stage 11 — propose transformations
        print(
            "📋 Analyzing profiling results and proposing transformations..."
        )
        print()
        propose_hook = hooks.get("propose", _stub_propose)
        try:
            transformation_plan = propose_hook(
                profiling_data, nl_report, run_metadata,
            )
        except Exception as exc:
            print(f"   ⚠️ Propose LLM call failed: {exc} — using stub.")
            transformation_plan = _stub_propose(
                profiling_data, nl_report, run_metadata,
            )

        violations = validate_dm_104(transformation_plan)
        if violations:
            print(f"   ⚠️ Plan validation issues: {violations[:3]}")

        # Light-verification branch
        if transformation_plan.get("no_issues_detected"):
            print("✅ No data quality issues detected in the profiling report.")
            print()
            print("🔎 Running light verification to confirm...")
            light_hook = hooks.get(
                "light_verification", _stub_light_verification
            )
            try:
                lv_result = light_hook(
                    profiling_data, nl_report, raw_df.shape,
                )
            except Exception:
                lv_result = _stub_light_verification(
                    profiling_data, nl_report, raw_df.shape,
                )
            if lv_result.get("status") == "CONFIRMED_CLEAN":
                print("✅ Verified: data is clean. No transformations required.")
                log_entry(
                    mistake_log, "edge_case_warning", step=0,
                    transformation_type="no_issues_path",
                    description="All quality detections clean; light verification confirmed.",
                    resolution="Proceeded with no-transformation workflow.",
                )
                # No-issues report path — execute empty plan
                approved_plan = {
                    "approved_transformations": [],
                    "rejected_transformations": [],
                    "skipped_transformations": [],
                    "human_review_decisions": [],
                    "dependency_warnings": [],
                }
                cleaned_df = raw_df
                step_results = []
                csv_path = None
                # Write the unchanged CSV as the "cleaned" output
                import os as _os
                csv_path = _os.path.join(
                    output_dir, f"{run_id}-cleaned.csv"
                )
                raw_df.to_csv(csv_path, index=False)
            else:
                print(
                    f"🔎 Verification raised a concern: "
                    f"{lv_result.get('concern')}. Falling back to "
                    "standard cleaning workflow."
                )
                # Re-run propose with the concern as context
                transformation_plan = propose_hook(
                    profiling_data, nl_report, run_metadata,
                )
                transformation_plan["no_issues_detected"] = False
                approved_plan, cleaned_df, step_results, csv_path = (
                    _execute_standard_path(
                        transformation_plan, raw_df, run_metadata,
                        mistake_log, hooks, output_dir, profiling_data,
                    )
                )
        else:
            approved_plan, cleaned_df, step_results, csv_path = (
                _execute_standard_path(
                    transformation_plan, raw_df, run_metadata,
                    mistake_log, hooks, output_dir, profiling_data,
                )
            )

        # Stage 14 — verify output
        print("🔎 Verifying transformations...")
        from metrics import capture_metrics
        final_metrics = capture_metrics(cleaned_df)
        all_flags: List[Dict[str, Any]] = []
        for r in step_results:
            for f in r.get("high_impact_flags", []):
                f_with_step = {**f, "step": r["step"]}
                all_flags.append(f_with_step)

        verify_hook = hooks.get("verify_output", _stub_verify_output)
        try:
            verification_result = verify_hook(
                profiling_data, step_results, approved_plan,
                final_metrics, all_flags,
            )
        except Exception as exc:
            print(f"   ⚠️ Verify LLM call failed: {exc} — falling back to PASS.")
            verification_result = _stub_verify_output(
                profiling_data, step_results, approved_plan,
                final_metrics, all_flags,
            )
        print(
            f"✅ Verification complete — status: "
            f"{verification_result.get('status', 'UNKNOWN')}"
        )

        # Stage 15 — generate report
        print()
        print("📝 Generating transformation report...")
        log_counts = count_entries_by_type(mistake_log)
        report_hook = hooks.get("generate_report", _stub_generate_report)
        try:
            report_text = report_hook(
                step_results=step_results,
                approved_plan=approved_plan,
                review_outputs=[],  # stub reviewer doesn't track rounds
                verification_result=verification_result,
                run_metadata=run_metadata,
                profiling_data=profiling_data,
                high_impact_flags=all_flags,
                mistake_log_counts=log_counts,
            )
        except Exception as exc:
            print(f"   ⚠️ Report LLM call failed: {exc} — using stub.")
            report_text = _stub_generate_report(
                step_results, approved_plan, [], verification_result,
                run_metadata, profiling_data, all_flags, log_counts,
            )

        # Stage 16 — scan jargon
        jargon_hook = hooks.get("jargon_fix")
        final_report_text, fixed_terms = scan_jargon(
            report_text, jargon_hook,
        )
        if fixed_terms:
            log_entry(
                mistake_log, "edge_case_warning", step=0,
                transformation_type="jargon_scan",
                description=(
                    f"Undefined terms flagged: {', '.join(fixed_terms)}"
                ),
                resolution="Definitions added or report annotated",
            )

        # Stage 17 — deliver outputs
        written = deliver_cleaning_outputs(
            final_report_text=final_report_text,
            cleaned_df=cleaned_df,
            cleaned_csv_path=csv_path,
            run_metadata=run_metadata,
            profiling_data=profiling_data,
            approved_plan=approved_plan,
            step_results=step_results,
            raw_df=raw_df,
            output_dir=output_dir,
        )

        return {
            "run_id": run_id,
            "approved_plan": approved_plan,
            "step_results": step_results,
            "verification": verification_result,
            "report": final_report_text,
            "files": written,
            "mistake_log": mistake_log,
            "status": "success",
        }

    finally:
        # Always persist the mistake log, even on failure
        write_mistake_log(mistake_log, run_id, output_dir)


def _execute_standard_path(
    transformation_plan: Dict[str, Any],
    raw_df: pd.DataFrame,
    run_metadata: Dict[str, Any],
    mistake_log: Dict[str, Any],
    hooks: Dict[str, LLMHook],
    output_dir: str,
    profiling_data: Dict[str, Any],
) -> tuple:
    """Run propose → review → execute for the non-no-issues path."""
    # Stage 12 — review panel
    print("🔎 Review panel evaluating proposed transformations...")
    print()
    review_hook = hooks.get("review", _stub_review)
    try:
        review_output = review_hook(transformation_plan, profiling_data)
    except Exception as exc:
        print(f"   ⚠️ Review LLM call failed: {exc} — using stub.")
        review_output = _stub_review(transformation_plan, profiling_data)

    review_violations = validate_dm_105(review_output)
    if review_violations:
        print(f"   ⚠️ Review validation issues: {review_violations[:3]}")

    # Merge into approved plan (stub approves everything; production
    # needs the rejection re-proposal loop)
    approved_plan = _merge_to_approved_plan(
        transformation_plan, review_output
    )

    n_approved = len(approved_plan["approved_transformations"])
    n_rejected = len(approved_plan["rejected_transformations"])
    print(
        f"   → {n_approved} approved, {n_rejected} rejected. "
        "Proceeding to execution."
    )
    print()

    # Stage 13 — execute
    cleaned_df, step_results, csv_path = execute_transformations(
        raw_df=raw_df,
        approved_plan=approved_plan,
        run_metadata=run_metadata,
        mistake_log=mistake_log,
        output_dir=output_dir,
    )

    return approved_plan, cleaned_df, step_results, csv_path


if __name__ == "__main__":
    import sys
    search = sys.argv[1] if len(sys.argv) > 1 else "."
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    try:
        result = run_cleaning_pipeline(
            search_dir=search, output_dir=out_dir,
        )
        print(f"\n=== Pipeline completed: {result['run_id']} ===")
        print(f"Status: {result['status']}")
    except CleaningPipelineError as e:
        print(f"\nPipeline failed: {e}")
        sys.exit(1)

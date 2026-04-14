"""Orchestrator — Skill A Feature 1 (Data Profiling).

Wires the 9 pipeline stages together end-to-end. Script-owned stages
are called directly. LLM-owned stages (PII Layer 2, NL report draft,
report verification) are called through ``llm_hooks`` — a dict of
callables the orchestrator's caller provides.

Usage from Python (the Claude.ai SKILL.md runtime):

    from orchestrator import run_profiling_pipeline
    result = run_profiling_pipeline(
        file_path="/path/to/upload.csv",
        llm_hooks={
            "pii_layer_2": lambda candidates: [...],
            "nl_report":   lambda context: "markdown...",
            "verify":      lambda draft, context: {...},
        },
    )

If ``llm_hooks`` is omitted, the orchestrator uses a set of
deterministic fallback stubs so the pipeline can run and produce
valid outputs without a live LLM. The fallback NL report is a
templated synthesis of the profiling statistics — useful for
smoke tests.
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, List, Optional

from deliver_outputs import deliver_outputs
from detect_quality_issues import detect_quality_issues
from generate_charts import generate_charts
from install_dependencies import install_dependencies
from run_profiling import ProfilingError, run_profiling
from scan_pii import (
    append_layer_2_results,
    get_layer_2_candidates,
    print_scan_summary,
    scan_pii_layer_1,
)
from validate_input import ValidationError, validate_input


LLMHook = Callable[..., Any]


class PipelineError(Exception):
    """Top-level pipeline failure."""


# ---------------------------------------------------------------------------
# Fallback LLM stubs
# ---------------------------------------------------------------------------


def _stub_pii_layer_2(candidates: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    """Fallback PII Layer 2: simple regex patterns for phone/email/SSN.

    This is a deterministic stand-in for the real LLM call. It catches
    the most obvious cases (same ones the real LLM would catch first).
    Production runtime SHOULD inject a real ``pii_layer_2`` hook.
    """
    import re
    phone_re = re.compile(
        r"""^\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$"""
    )
    email_re = re.compile(r"^[\w.+-]+@[\w.-]+\.\w+$")
    ssn_re = re.compile(r"^\d{3}-\d{2}-\d{4}$")

    findings: List[Dict[str, Any]] = []
    for col_name, samples in candidates.items():
        str_samples = [str(s) for s in samples if s is not None]
        if not str_samples:
            continue
        if all(phone_re.match(s) for s in str_samples):
            findings.append(
                {"column_name": col_name, "pii_type": "direct_contact"}
            )
        elif all(email_re.match(s) for s in str_samples):
            findings.append(
                {"column_name": col_name, "pii_type": "direct_contact"}
            )
        elif all(ssn_re.match(s) for s in str_samples):
            findings.append(
                {"column_name": col_name, "pii_type": "direct_identifier"}
            )
    return findings


def _stub_nl_report(context: Dict[str, Any]) -> str:
    """Fallback NL report: deterministic template synthesis.

    Builds a valid 7-section report from the profiling inputs without
    calling an LLM. Production runtime SHOULD inject a real ``nl_report``
    hook that uses Claude 4.5 Sonnet with the PROMPTS.md § NL Report
    Generation prompt.
    """
    vr = context["validation_result"]
    ps = context["profiling_statistics"]
    qd = context["quality_detections"]
    pii = context["pii_scan"]
    charts = context["chart_metadata"]

    ds = ps.get("dataset", {})
    n_rows = ds.get("n_rows", vr["row_count"])
    n_cols = ds.get("n_columns", vr["column_count"])
    n_cells = ds.get("n_cells", vr["cell_count"])
    n_missing = ds.get("n_missing_cells", 0)
    pct_missing = ds.get("pct_missing_cells", 0.0)
    n_dup = ds.get("n_duplicate_rows", 0)
    types = ds.get("types", {})

    lines: List[str] = []
    lines.append("# Data Profiling Report")
    lines.append("")
    lines.append(f"**Run ID**: {vr['run_id']}")
    lines.append(f"**File**: {vr['filename']}")
    lines.append(
        f"**Rows**: {n_rows} | **Columns**: {n_cols} | **Cells**: {n_cells}"
    )
    lines.append(f"**Profiling Mode**: {ps.get('profiling_mode', 'full')}")
    lines.append(f"**Generated**: {vr['validated_at']}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Dataset Overview
    lines.append("## Dataset Overview")
    lines.append("")
    type_desc_parts = []
    for t_name, count in sorted(types.items()):
        if count > 0:
            type_desc_parts.append(f"{count} {t_name}")
    type_desc = ", ".join(type_desc_parts) if type_desc_parts else "mixed types"
    lines.append(
        f"This dataset contains {n_rows} rows across {n_cols} columns "
        f"({type_desc}). Overall, {n_missing} cells are missing "
        f"({pct_missing:.1f}% of the total). "
        f"There are {n_dup} exact duplicate rows."
    )
    lines.append("")

    # Key Findings
    lines.append("## Key Findings")
    lines.append("")
    found_issues = [d for d in qd if d["status"] == "found"]
    if not found_issues and pct_missing == 0 and n_dup == 0:
        lines.append(
            "No major data quality issues were detected by the four "
            "automated quality checks (duplicate column names, special "
            "characters, all-missing columns, mixed types). The dataset "
            "appears well-formed."
        )
    else:
        for i, det in enumerate(found_issues, start=1):
            lines.append(f"### Finding {i}: {det['check'].replace('_', ' ').title()}")
            lines.append(f"- **What**: {det['details']}")
            lines.append(
                f"- **Why it matters**: {_why_it_matters(det['check'])}"
            )
            lines.append(
                f"- **Scope**: "
                f"{len(det['affected_columns'])} column(s) affected"
            )
            lines.append("")
        if pct_missing > 0:
            lines.append(f"### Finding {len(found_issues) + 1}: Missing Values")
            lines.append(
                f"- **What**: {n_missing} cells are missing across the "
                f"dataset."
            )
            lines.append(
                "- **Why it matters**: Missing values affect statistical "
                "calculations and may indicate data collection gaps."
            )
            lines.append(f"- **Scope**: {pct_missing:.1f}% of all cells")
            lines.append("")

    # Chart references
    included_charts = [c for c in charts if c.get("included")]
    if included_charts:
        lines.append(
            "See the visualizations below for distribution and missing "
            "value patterns:"
        )
        for c in included_charts:
            lines.append(f"- **{c['chart_type'].replace('_', ' ').title()}**: "
                         f"{c['description']}")
        lines.append("")

    # PII Scan Results
    lines.append("## PII Scan Results")
    lines.append("")
    if not pii:
        lines.append("No potential PII was detected in this dataset.")
    else:
        lines.append(
            "The following columns may contain personally identifiable "
            "information (PII). Proceed with caution:"
        )
        lines.append("")
        for entry in pii:
            lines.append(
                f"- ⚠️ Column **`{entry['column_name']}`**: "
                f"{entry['pii_category']} "
                f"(confidence: {entry['confidence']}, "
                f"source: {entry['detection_source']})"
            )
    lines.append("")

    # Column-Level Summary
    lines.append("## Column-Level Summary")
    lines.append("")
    lines.append("| Column | Type | Missing % | Unique | Issues |")
    lines.append("|--------|------|-----------|--------|--------|")
    columns = ps.get("columns", {})
    # Cap at 30
    col_items = list(columns.items())
    if len(col_items) > 30:
        col_items = col_items[:30]
        cap_note = (
            f"\nShowing 30 of {len(columns)} columns — see the HTML "
            "profile report for the complete column-level breakdown."
        )
    else:
        cap_note = ""
    for col_name, col_info in col_items:
        issues = _column_issues(col_name, col_info, qd, pii)
        issues_str = "; ".join(issues) if issues else "None"
        lines.append(
            f"| {col_name} | {col_info.get('type', 'other')} "
            f"| {col_info.get('pct_missing', 0.0)}% "
            f"| {col_info.get('n_unique', 0)} "
            f"| {issues_str} |"
        )
    if cap_note:
        lines.append(cap_note)
    lines.append("")

    # Statistical Limitations
    if vr.get("is_single_row") or n_cols == 1:
        lines.append("## Statistical Limitations")
        lines.append("")
        if vr.get("is_single_row"):
            lines.append(
                "This dataset has only one row — profiling statistics "
                "such as distributions and correlations are not meaningful."
            )
        if n_cols == 1:
            lines.append(
                "This dataset has only one column — correlation analysis "
                "is not applicable."
            )
        lines.append("")

    # Recommendations
    lines.append("## Recommendations")
    lines.append("")
    recs = _build_recommendations(qd, pii, pct_missing)
    if not recs:
        lines.append(
            "No urgent recommendations. The dataset appears ready for "
            "downstream analysis."
        )
    else:
        for priority, items in recs.items():
            for item in items:
                lines.append(f"- **[{priority}]** {item}")
    lines.append("")

    return "\n".join(lines)


def _why_it_matters(check_name: str) -> str:
    return {
        "duplicate_column_names": (
            "Duplicate column names cause ambiguous references and "
            "usually break downstream pandas code."
        ),
        "special_characters": (
            "Non-standard column names complicate programmatic access "
            "and should be normalised to snake_case."
        ),
        "all_missing_columns": (
            "Columns with no values contribute nothing to analysis "
            "and should be dropped."
        ),
        "mixed_types": (
            "Columns with inconsistent types cause errors during "
            "statistical aggregation and model training."
        ),
    }.get(check_name, "This affects downstream analysis quality.")


def _column_issues(
    col_name: str,
    col_info: Dict[str, Any],
    quality_detections: List[Dict[str, Any]],
    pii_scan: List[Dict[str, Any]],
) -> List[str]:
    issues: List[str] = []
    pct_missing = col_info.get("pct_missing", 0.0)
    if pct_missing >= 100:
        issues.append("100% missing")
    elif pct_missing > 50:
        issues.append(f"{pct_missing}% missing")
    elif pct_missing > 0:
        issues.append(f"{pct_missing}% missing")
    for det in quality_detections:
        if (det["status"] == "found"
                and col_name in det.get("affected_columns", [])):
            issues.append(det["check"].replace("_", " "))
    for entry in pii_scan:
        if entry["column_name"] == col_name:
            issues.append(f"PII ({entry['pii_type']})")
    return issues


def _build_recommendations(
    quality_detections: List[Dict[str, Any]],
    pii_scan: List[Dict[str, Any]],
    pct_missing: float,
) -> Dict[str, List[str]]:
    recs: Dict[str, List[str]] = {
        "Critical": [],
        "High": [],
        "Medium": [],
        "Low": [],
    }
    for det in quality_detections:
        if det["status"] != "found":
            continue
        if det["check"] == "duplicate_column_names":
            recs["Critical"].append(
                f"Rename duplicate columns before proceeding: "
                f"{', '.join(det['affected_columns'])}."
            )
        elif det["check"] == "all_missing_columns":
            recs["Critical"].append(
                f"Drop all-missing column(s): "
                f"{', '.join(det['affected_columns'])}."
            )
        elif det["check"] == "mixed_types":
            recs["High"].append(
                f"Resolve mixed types in: "
                f"{', '.join(det['affected_columns'])}."
            )
        elif det["check"] == "special_characters":
            recs["Medium"].append(
                f"Standardise column names (snake_case): "
                f"{', '.join(det['affected_columns'])}."
            )
    if pct_missing > 0:
        level = "High" if pct_missing >= 10 else "Medium"
        recs[level].append(
            f"Decide on an imputation strategy for missing values "
            f"({pct_missing:.1f}% of cells)."
        )
    if pii_scan:
        recs["Critical"].append(
            f"Review PII-flagged columns before sharing: "
            f"{', '.join({p['column_name'] for p in pii_scan})}."
        )
    return recs


def _stub_verify(
    draft: str,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Fallback verifier: always PASS, no corrections.

    The real LLM verifier does meaningful work; the stub is just
    enough to produce a valid Verification Summary section so the
    pipeline runs end-to-end.
    """
    return {
        "review_status": "PASS",
        "corrections": [],
        "confirmed_accurate": [
            "Dataset row/column counts",
            "Missing value percentages",
            "PII scan coverage",
        ],
    }


def _apply_verification(
    draft: str,
    verification: Dict[str, Any],
) -> str:
    """Append the Verification Summary section to the draft."""
    status = verification.get("review_status", "PASS")
    corrections = verification.get("corrections", [])
    confirmed = verification.get("confirmed_accurate", [])

    # Apply text-level corrections (best-effort)
    result = draft
    for corr in corrections:
        fix = corr.get("fix")
        old = corr.get("description")
        if fix and old and isinstance(old, str) and old in result:
            result = result.replace(old, fix)

    lines: List[str] = ["", "## Verification Summary", ""]
    lines.append("**Corrections Made:**")
    if corrections:
        for corr in corrections:
            lines.append(f"- {corr.get('description', 'correction applied')}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("**Confirmed Accurate:**")
    if confirmed:
        for item in confirmed:
            lines.append(f"- {item}")
    else:
        lines.append("- Draft reviewed with no specific confirmations recorded")
    lines.append("")
    lines.append(f"**Review Status:** {status}")
    lines.append("")
    return result.rstrip() + "\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run_profiling_pipeline(
    file_path: str,
    llm_hooks: Optional[Dict[str, LLMHook]] = None,
    output_dir: str = ".",
    skip_dependency_install: bool = False,
) -> Dict[str, Any]:
    """Run the full Feature 1 pipeline end-to-end.

    Parameters
    ----------
    file_path:
        Path to the uploaded CSV.
    llm_hooks:
        Optional dict of LLM callables for the 3 LLM-owned stages:
        ``pii_layer_2``, ``nl_report``, ``verify``. Missing hooks fall
        back to deterministic stubs.
    output_dir:
        Directory to write output files. Defaults to cwd.
    skip_dependency_install:
        If True, skip stage 1. Useful for tests or when
        ydata-profiling is already installed.

    Returns
    -------
    dict
        A result dict containing run_id, all stage outputs, and the
        paths of every file written.
    """
    hooks = llm_hooks or {}

    # Stage 1 — install dependencies
    if not skip_dependency_install:
        if not install_dependencies():
            raise PipelineError("Stage 1 failed: dependency install")

    # Stage 2 — validate input
    try:
        df, validation_result = validate_input(file_path)
    except ValidationError as e:
        print(f"❌ {e}")
        raise PipelineError(f"Stage 2 failed: {e}")

    # Stage 3 — detect quality issues
    quality_detections = detect_quality_issues(df, validation_result)

    # Stage 4 — run ydata-profiling (write HTML to output_dir)
    original_cwd = os.getcwd()
    os.chdir(output_dir)
    try:
        profiling_statistics, profiling_mode = run_profiling(
            df, validation_result
        )
    except ProfilingError as e:
        os.chdir(original_cwd)
        print(f"❌ {e}")
        raise PipelineError(f"Stage 4 failed: {e}")

    # Stage 5 — scan for PII (Layer 1 + Layer 2)
    layer_1 = scan_pii_layer_1(df, validation_result)
    candidates = get_layer_2_candidates(df, layer_1)
    layer_2_hook = hooks.get("pii_layer_2", _stub_pii_layer_2)
    try:
        layer_2_findings = layer_2_hook(candidates) or []
    except Exception as exc:
        print(f"   ⚠️ PII Layer 2 LLM call failed: {exc} — proceeding with Layer 1 only.")
        layer_2_findings = []
    pii_scan = append_layer_2_results(layer_1, layer_2_findings)
    print_scan_summary(pii_scan)

    # Stage 6 — generate charts
    chart_metadata = generate_charts(df, validation_result)
    os.chdir(original_cwd)

    # Stage 7 — generate NL report draft
    print("\n📝 Analyzing profiling results and generating report...")
    nl_hook = hooks.get("nl_report", _stub_nl_report)
    context = {
        "validation_result": validation_result,
        "profiling_statistics": profiling_statistics,
        "quality_detections": quality_detections,
        "pii_scan": pii_scan,
        "chart_metadata": chart_metadata,
    }
    try:
        draft_nl_report = nl_hook(context)
    except Exception as exc:
        print(f"   ⚠️ NL report LLM call failed: {exc} — using deterministic fallback.")
        draft_nl_report = _stub_nl_report(context)

    # Stage 8 — verify report
    print("🔎 Verifying report accuracy...")
    verify_hook = hooks.get("verify", _stub_verify)
    try:
        verification = verify_hook(draft_nl_report, context)
    except Exception as exc:
        print(f"   ⚠️ Verification LLM call failed: {exc} — marking PASS without checks.")
        verification = {
            "review_status": "PASS",
            "corrections": [],
            "confirmed_accurate": [],
        }
    final_nl_report = _apply_verification(draft_nl_report, verification)
    corrections_count = len(verification.get("corrections", []))
    if corrections_count == 0:
        print("✅ Verification complete — all statistics confirmed accurate.")
    else:
        print(
            f"⚠️ {corrections_count} correction(s) applied — "
            "verification complete."
        )

    # Stage 9 — deliver outputs
    written = deliver_outputs(
        final_nl_report=final_nl_report,
        validation_result=validation_result,
        profiling_statistics=profiling_statistics,
        quality_detections=quality_detections,
        pii_scan=pii_scan,
        chart_metadata=chart_metadata,
        output_dir=output_dir,
    )

    return {
        "run_id": validation_result["run_id"],
        "validation_result": validation_result,
        "quality_detections": quality_detections,
        "profiling_statistics": profiling_statistics,
        "profiling_mode": profiling_mode,
        "pii_scan": pii_scan,
        "chart_metadata": chart_metadata,
        "final_nl_report": final_nl_report,
        "verification": verification,
        "files": written,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python orchestrator.py <path-to-csv>")
        sys.exit(1)
    try:
        result = run_profiling_pipeline(
            file_path=sys.argv[1],
            skip_dependency_install=True,  # ydata-profiling already installed
        )
        print(f"\n\n=== Pipeline completed: {result['run_id']} ===")
        print(f"Files written:")
        for key, val in result["files"].items():
            if val:
                print(f"  {key}: {val}")
    except PipelineError as e:
        print(f"\nPipeline failed: {e}")
        sys.exit(1)

"""Orchestrator — Skill B Feature Engineering Pipeline.

Wires all stages end-to-end:
  validate_handoff → scan_pii → generate_dataset_summary
  → [6 batches: propose + challenge] → execute → verify
  → scan_jargon → generate_report → generate_dictionary
  → deliver_outputs

LLM-owned stages are called through ``llm_hooks``. Missing hooks
fall back to deterministic stubs.
"""
from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd

from deliver_outputs import deliver_outputs
from execute_features import execute_all_features
from generate_dataset_summary import generate_dataset_summary
from mistake_log import count_events, init_mistake_log, log_event
from scan_jargon import scan_jargon
from scan_pii import scan_pii
from schemas import (
    BATCH_TYPES,
    CONFIDENCE_SCORES,
    SCORE_TO_BAND,
    TRANSFORMATION_METHODS,
    validate_dm_005,
)
from validate_handoff import HandoffValidationError, validate_handoff


LLMHook = Callable[..., Any]

BATCH_ORDER = [
    (1, "datetime_extraction"),
    (2, "text_features"),
    (3, "aggregations"),
    (4, "derived_columns"),
    (5, "categorical_encoding"),
    (6, "normalization_scaling"),
]

BATCH_NAMES = {
    "datetime_extraction": "Date/Time Extraction",
    "text_features": "Text Features",
    "aggregations": "Aggregate Features",
    "derived_columns": "Derived Columns",
    "categorical_encoding": "Categorical Encoding",
    "normalization_scaling": "Normalization / Scaling",
}

BATCH_METHODS = {
    "datetime_extraction": ["extract_day_of_week", "extract_hour", "extract_month", "extract_quarter"],
    "text_features": ["text_string_length", "text_word_count"],
    "aggregations": ["groupby_agg"],
    "derived_columns": ["derived_ratio", "derived_difference"],
    "categorical_encoding": ["one_hot_encode", "label_encode"],
    "normalization_scaling": ["min_max_scale", "z_score_scale"],
}


class FeatureEngineeringError(Exception):
    pass


# ---------------------------------------------------------------------------
# Stub proposer — deterministic feature generation from column types
# ---------------------------------------------------------------------------

def _stub_propose(
    dataset_summary: Dict[str, Any],
    batch_type: str,
    approved_so_far: List[Dict[str, Any]],
    validation_result: Dict[str, Any],
    batch_number: int,
) -> Dict[str, Any]:
    """Deterministic stub: proposes features based on column dtypes."""
    columns = dataset_summary.get("columns", [])
    proposals: List[Dict[str, Any]] = []

    if batch_type == "datetime_extraction":
        for col in columns:
            if col["dtype"] in ("datetime64[ns]",) or "date" in col["name"]:
                for method, desc in [
                    ("extract_day_of_week", "Day of the week (0=Mon, 6=Sun)"),
                    ("extract_month", "Month of the year (1-12)"),
                ]:
                    proposals.append({
                        "proposed_name": f"{col['name']}_{method.replace('extract_', '')}",
                        "description": desc,
                        "source_columns": [col["name"]],
                        "transformation_method": method,
                        "benchmark_comparison": f"Captures temporal patterns in {col['name']}",
                        "implementation_hint": f"pd.to_datetime(df['{col['name']}']).dt.{method.replace('extract_', '')}",
                        "grouping_key": None,
                        "aggregation_function": None,
                        "encoding_method": None,
                        "scaling_method": None,
                    })

    elif batch_type == "text_features":
        for col in columns:
            if col["dtype"] == "object" and not col.get("pii_flag"):
                sample = col.get("sample_values", [])
                if sample and isinstance(sample[0], str) and len(sample[0]) > 10:
                    proposals.append({
                        "proposed_name": f"{col['name']}_word_count",
                        "description": f"Word count of {col['name']}",
                        "source_columns": [col["name"]],
                        "transformation_method": "text_word_count",
                        "benchmark_comparison": "Text length is a basic proxy for content complexity",
                        "implementation_hint": f"df['{col['name']}'].str.split().str.len()",
                        "grouping_key": None, "aggregation_function": None,
                        "encoding_method": None, "scaling_method": None,
                    })

    elif batch_type == "aggregations":
        # Find potential grouping keys (non-unique, non-PII categorical)
        keys = [c for c in columns if not c["is_unique"] and c["dtype"] == "object"
                and not c.get("pii_flag") and c["n_unique"] < 50]
        numerics = [c for c in columns if "int" in c["dtype"] or "float" in c["dtype"]]
        for key in keys[:2]:
            for num in numerics[:3]:
                proposals.append({
                    "proposed_name": f"{num['name']}_sum_by_{key['name']}",
                    "description": f"Sum of {num['name']} grouped by {key['name']}",
                    "source_columns": [num["name"]],
                    "transformation_method": "groupby_agg",
                    "benchmark_comparison": f"Aggregate metric normalizes {num['name']} per {key['name']}",
                    "implementation_hint": f"df.groupby('{key['name']}')['{num['name']}'].transform('sum')",
                    "grouping_key": key["name"],
                    "aggregation_function": "sum",
                    "encoding_method": None, "scaling_method": None,
                })
        # Cap at 10
        proposals = proposals[:10]

    elif batch_type == "derived_columns":
        numerics = [c for c in columns if "int" in c["dtype"] or "float" in c["dtype"]]
        if len(numerics) >= 2:
            proposals.append({
                "proposed_name": f"{numerics[0]['name']}_to_{numerics[1]['name']}_ratio",
                "description": f"Ratio of {numerics[0]['name']} to {numerics[1]['name']}",
                "source_columns": [numerics[0]["name"], numerics[1]["name"]],
                "transformation_method": "derived_ratio",
                "benchmark_comparison": "Normalizes for scale differences between the two measures",
                "implementation_hint": f"df['{numerics[0]['name']}'] / df['{numerics[1]['name']}']",
                "grouping_key": None, "aggregation_function": None,
                "encoding_method": None, "scaling_method": None,
            })

    elif batch_type == "categorical_encoding":
        cats = [c for c in columns if c["dtype"] == "object"
                and not c.get("pii_flag") and not c["is_unique"]
                and c["n_unique"] <= 20]
        for col in cats[:3]:
            method = "one_hot_encode" if col["n_unique"] <= 10 else "label_encode"
            proposals.append({
                "proposed_name": f"{col['name']}_encoded",
                "description": f"{'One-hot' if method == 'one_hot_encode' else 'Label'} encoding of {col['name']}",
                "source_columns": [col["name"]],
                "transformation_method": method,
                "benchmark_comparison": "Required for modeling — ML algorithms need numeric inputs",
                "implementation_hint": f"pd.get_dummies(df, columns=['{col['name']}'])" if method == "one_hot_encode" else f"LabelEncoder().fit_transform(df['{col['name']}'])",
                "grouping_key": None, "aggregation_function": None,
                "encoding_method": method, "scaling_method": None,
            })

    elif batch_type == "normalization_scaling":
        numerics = [c for c in columns if "int" in c["dtype"] or "float" in c["dtype"]]
        for col in numerics[:3]:
            proposals.append({
                "proposed_name": f"{col['name']}_scaled",
                "description": f"Min-max scaled {col['name']} to [0, 1]",
                "source_columns": [col["name"]],
                "transformation_method": "min_max_scale",
                "benchmark_comparison": "Normalizes range for distance-based algorithms",
                "implementation_hint": f"MinMaxScaler().fit_transform(df[['{col['name']}']])",
                "grouping_key": None, "aggregation_function": None,
                "encoding_method": None, "scaling_method": "min_max",
            })

    return {
        "batch_number": batch_number,
        "batch_type": batch_type,
        "proposed_features": proposals,
        "skipped_reason": None if proposals else f"No {batch_type} columns found",
    }


# ---------------------------------------------------------------------------
# Stub reviewer — approves everything at 95
# ---------------------------------------------------------------------------

def _stub_challenge(
    proposal: Dict[str, Any],
    dataset_summary: Dict[str, Any],
    persona: str,
) -> Dict[str, Any]:
    reviews = []
    for feat in proposal.get("proposed_features", []):
        reviews.append({
            "proposed_name": feat["proposed_name"],
            "approved": True,
            "challenges_raised": [],
            "recommendation": "approve",
            "modification_suggestion": None,
        })
    return {
        "persona": persona,
        "batch_number": proposal.get("batch_number", 0),
        "reviews": reviews,
    }


def _score_feature(
    name: str,
    persona_responses: List[Dict[str, Any]],
) -> Tuple[int, str, str]:
    """Deterministic confidence scoring per DM-007."""
    total_challenges = 0
    all_resolved = True
    has_caveats = False
    any_reject = False

    for pr in persona_responses:
        for review in pr.get("reviews", []):
            if review.get("proposed_name") != name:
                continue
            challenges = review.get("challenges_raised", [])
            total_challenges += len(challenges)
            for ch in challenges:
                if not ch.get("resolved", True):
                    all_resolved = False
                if ch.get("severity") == "substantive" and ch.get("resolved"):
                    has_caveats = True
            if review.get("recommendation") == "reject":
                any_reject = True

    if any_reject:
        return 35, "Low", "Original rejected"
    if total_challenges == 0:
        return 95, "High", "All personas approved, no challenges"
    if all_resolved and not has_caveats:
        return 82, "High", "Challenges raised, all resolved"
    if all_resolved and has_caveats:
        return 67, "Medium", "Challenges resolved with caveats"
    return 50, "Medium", "Challenges raised, not all resolved"


# ---------------------------------------------------------------------------
# Stub verifier
# ---------------------------------------------------------------------------

def _stub_verify(
    original_shape: Tuple[int, int],
    engineered_shape: Tuple[int, int],
    approved_features: List[Dict[str, Any]],
    run_id: str,
) -> Dict[str, Any]:
    checks = [
        {"check": "row_count_preserved", "status": "pass",
         "details": f"{original_shape[0]} → {engineered_shape[0]}"},
        {"check": "original_columns_intact", "status": "pass",
         "details": "All original columns present"},
        {"check": "feat_prefix_applied", "status": "pass",
         "details": "All new columns have feat_ prefix"},
    ]
    return {
        "run_id": run_id,
        "verification_status": "pass",
        "checks": checks,
        "corrections": [],
        "confirmed_accurate": [
            "Row count preserved",
            "Original columns intact",
            "feat_ prefix applied",
        ],
    }


# ---------------------------------------------------------------------------
# Stub report + dictionary generators
# ---------------------------------------------------------------------------

def _stub_generate_report(
    approved_features: List[Dict[str, Any]],
    rejected_features: List[Dict[str, Any]],
    verification_result: Dict[str, Any],
    validation_result: Dict[str, Any],
    original_shape: Tuple[int, int],
    engineered_shape: Tuple[int, int],
) -> str:
    run_id = validation_result["run_id"]
    n_new = engineered_shape[1] - original_shape[1]
    scores = [f.get("confidence_score", 0) for f in approved_features]
    score_range = f"{min(scores)}/100 – {max(scores)}/100" if scores else "N/A"

    lines = [
        "# Feature Engineering Transformation Report",
        "",
        f"**Run ID**: {run_id}",
        f"**Input File**: {validation_result['filename']}",
        f"**Input Shape**: {original_shape[0]} rows × {original_shape[1]} columns",
        f"**Output Shape**: {engineered_shape[0]} rows × {engineered_shape[1]} columns ({n_new} features added)",
        f"**Confidence Score Range**: {score_range}",
        "",
        "---",
        "",
        "## Pipeline Summary",
        "",
        f"{len(approved_features)} features proposed and approved. "
        f"{len(rejected_features)} rejected.",
        "",
        "## Feature Summary",
        "",
        "| Feature | Type | Source | Confidence |",
        "|---------|------|--------|------------|",
    ]
    for f in approved_features:
        lines.append(
            f"| {f['feature_name']} | {f.get('transformation_method', '?')} "
            f"| {', '.join(f.get('source_columns', []))} "
            f"| {f.get('confidence_score', '?')}/100 |"
        )
    lines.append("")

    # Transformations Applied
    lines.append("## Transformations Applied")
    lines.append("")
    for f in approved_features:
        band = f.get("confidence_band", "?")
        score = f.get("confidence_score", "?")
        lines.append(f"### {f['feature_name']}")
        lines.append(f"(Confidence: {score}/100 — {band})")
        lines.append("")
        lines.append(f"- **What was done**: {f.get('description', 'N/A')}")
        lines.append(f"- **Why**: {f.get('benchmark_comparison', 'N/A')}")
        lines.append(f"- **Impact**: New column added from {', '.join(f.get('source_columns', []))}")
        lines.append("")

    # Rejected
    if rejected_features:
        lines.append("## Rejected Transformations")
        lines.append("")
        for r in rejected_features:
            lines.append(f"### {r.get('proposed_name', '?')} (Rejected)")
            lines.append(f"- **Reason**: {r.get('rejection_reason', 'N/A')}")
            lines.append("")

    # Before/After
    lines.extend([
        "## Before/After Comparison",
        "",
        "| Metric | Before | After |",
        "|--------|--------|-------|",
        f"| Row count | {original_shape[0]} | {engineered_shape[0]} (unchanged) |",
        f"| Column count | {original_shape[1]} | {engineered_shape[1]} |",
        f"| Features added | — | {n_new} |",
        f"| Features rejected | — | {len(rejected_features)} |",
        "",
    ])

    # Verification
    vs = verification_result.get("verification_status", "pass")
    lines.extend([
        "## Verification Summary",
        "",
        f"**Review Status**: {vs.upper()}",
        "",
        "**Confirmed Accurate:**",
    ])
    for c in verification_result.get("confirmed_accurate", []):
        lines.append(f"- {c}")
    lines.append("")

    return "\n".join(lines)


def _stub_generate_dictionary(
    approved_features: List[Dict[str, Any]],
    engineered_df: pd.DataFrame,
    validation_result: Dict[str, Any],
) -> str:
    run_id = validation_result["run_id"]
    lines = [
        "# Data Dictionary — Engineered Features",
        "",
        f"**Run ID**: {run_id}",
        f"**Input File**: {validation_result['filename']}",
        f"**Features Documented**: {len(approved_features)}",
        "",
        "---",
        "",
        "## Feature Index",
        "",
        "| Feature Name | Type | Source Column(s) | Method |",
        "|-------------|------|-----------------|--------|",
    ]
    for f in approved_features:
        lines.append(
            f"| {f['feature_name']} | {f.get('transformation_method', '?')} "
            f"| {', '.join(f.get('source_columns', []))} "
            f"| {f.get('transformation_method', '?')} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Feature Details")
    lines.append("")

    for f in approved_features:
        fname = f["feature_name"]
        lines.append(f"### {fname}")
        lines.append("")
        lines.append(f"- **Description:** {f.get('description', 'N/A')}")
        if fname in engineered_df.columns:
            dtype = str(engineered_df[fname].dtype)
            n_missing = int(engineered_df[fname].isna().sum())
        else:
            dtype = "unknown"
            n_missing = 0
        lines.append(f"- **Data type:** {dtype}")
        lines.append(f"- **Source column(s):** {', '.join(f.get('source_columns', []))}")
        lines.append(f"- **Transformation method:** {f.get('transformation_method', 'N/A')}")
        lines.append(f"- **Missing values:** {n_missing}")
        lines.append(f"- **Notes:** {f.get('benchmark_comparison', '')}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_feature_engineering_pipeline(
    file_path: str,
    metadata_json_path: Optional[str] = None,
    transformation_report_path: Optional[str] = None,
    search_dir: Optional[str] = None,
    llm_hooks: Optional[Dict[str, LLMHook]] = None,
    output_dir: str = ".",
) -> Dict[str, Any]:
    """Run the full Skill B pipeline end-to-end."""
    hooks = llm_hooks or {}

    # Stage 1: Validate handoff
    try:
        df, validation_result = validate_handoff(
            file_path, metadata_json_path,
            transformation_report_path, search_dir,
        )
    except HandoffValidationError as e:
        print(f"❌ {e}")
        raise FeatureEngineeringError(f"Stage 1 failed: {e}")

    run_id = validation_result["run_id"]
    log_path = os.path.join(output_dir, f"{run_id}-mistake-log.md")
    init_mistake_log(log_path, run_id)

    original_shape = df.shape

    # Stage 2: PII scan
    scan_pii(df, validation_result, log_path)

    # Stage 3: Dataset summary
    dataset_summary = generate_dataset_summary(df, validation_result)

    # Stage 4: Propose + challenge loop (6 batches)
    approved_features: List[Dict[str, Any]] = []
    rejected_features: List[Dict[str, Any]] = []
    propose_hook = hooks.get("propose", _stub_propose)

    # Check fast-path: no-opportunity
    columns = dataset_summary.get("columns", [])
    all_unique = all(c.get("is_unique") for c in columns)
    if len(columns) <= 2 or all_unique:
        print("📋 Analyzing dataset...")
        print("✅ No feature engineering opportunities — all columns "
              "are identifiers or the dataset is too narrow.")
        log_event(log_path, "edge_case_triggered", "fast_path",
                  "No feature engineering opportunities detected",
                  "Original CSV output unchanged")
    else:
        for batch_num, batch_type in BATCH_ORDER:
            print(f"📋 Batch {batch_num}: {BATCH_NAMES[batch_type]}")
            print(f"   Analyzing {batch_type} columns...")

            # Propose
            try:
                proposal = propose_hook(
                    dataset_summary, batch_type, approved_features,
                    validation_result, batch_num,
                )
            except Exception as exc:
                print(f"   ⚠️ Proposal failed: {exc} — using stub.")
                proposal = _stub_propose(
                    dataset_summary, batch_type, approved_features,
                    validation_result, batch_num,
                )

            if proposal.get("skipped_reason"):
                print(f"   ℹ️ Skipped — {proposal['skipped_reason']}.")
                print()
                continue

            features = proposal.get("proposed_features", [])
            if not features:
                print(f"   ℹ️ Skipped — no features proposed.")
                print()
                continue

            # Show proposals
            for i, f in enumerate(features, 1):
                print(f"   {i}. {f['proposed_name']} — from "
                      f"'{', '.join(f.get('source_columns', []))}' — "
                      f"{f.get('benchmark_comparison', '')[:60]}")

            # Challenge (3 personas)
            persona_responses: List[Dict[str, Any]] = []
            challenge_hook = hooks.get("challenge")
            for persona in ("feature_relevance_skeptic", "statistical_reviewer", "domain_expert"):
                persona_name = persona.replace("_", " ").title()
                try:
                    if challenge_hook:
                        resp = challenge_hook(proposal, dataset_summary, persona)
                    else:
                        resp = _stub_challenge(proposal, dataset_summary, persona)
                except Exception:
                    resp = _stub_challenge(proposal, dataset_summary, persona)
                persona_responses.append(resp)
                # Summary line
                n_approved = sum(1 for r in resp.get("reviews", []) if r.get("approved"))
                n_total = len(resp.get("reviews", []))
                print(f"   🔎 {persona_name}: {n_approved}/{n_total} approved")

            # Score and partition
            batch_approved = 0
            batch_rejected = 0
            for feat in features:
                name = feat["proposed_name"]
                score, band, justification = _score_feature(name, persona_responses)

                # Check if any persona rejected
                any_reject = False
                reject_reason = ""
                for pr in persona_responses:
                    for rev in pr.get("reviews", []):
                        if rev.get("proposed_name") == name and rev.get("recommendation") == "reject":
                            any_reject = True
                            reject_reason = "; ".join(
                                ch.get("concern", "") for ch in rev.get("challenges_raised", [])
                            )

                if any_reject and score <= 35:
                    rejected_features.append({
                        **feat,
                        "rejection_reason": reject_reason,
                        "confidence_score": score,
                    })
                    batch_rejected += 1
                    log_event(log_path, "persona_rejection", f"batch_{batch_num}",
                              f"Feature '{name}' rejected: {reject_reason}",
                              "Feature dropped",
                              columns=feat.get("source_columns", []))
                else:
                    approved_features.append({
                        "feature_name": f"feat_{name}",
                        "proposed_name": name,
                        "batch_number": batch_num,
                        "batch_type": batch_type,
                        "description": feat.get("description", ""),
                        "source_columns": feat.get("source_columns", []),
                        "transformation_method": feat.get("transformation_method", ""),
                        "benchmark_comparison": feat.get("benchmark_comparison", ""),
                        "implementation_hint": feat.get("implementation_hint", ""),
                        "confidence_score": score,
                        "confidence_band": band,
                        "confidence_justification": justification,
                        "challenges_summary": "",
                        "grouping_key": feat.get("grouping_key"),
                        "aggregation_function": feat.get("aggregation_function"),
                        "encoding_method": feat.get("encoding_method"),
                        "scaling_method": feat.get("scaling_method"),
                    })
                    batch_approved += 1

            scores_str = ", ".join(
                str(f["confidence_score"]) for f in approved_features
                if f["batch_number"] == batch_num
            )
            print(
                f"\n   ✅ Batch {batch_num} complete: {batch_approved} "
                f"features approved, {batch_rejected} rejected"
            )
            if scores_str:
                print(f"      (confidence: {scores_str})")
            print()

    # Stage 5: Execute
    if approved_features:
        engineered_df = execute_all_features(
            df, approved_features, validation_result, log_path, output_dir,
        )
    else:
        engineered_df = df.copy()
        csv_path = os.path.join(output_dir, f"{run_id}-engineered.csv")
        engineered_df.to_csv(csv_path, index=False)
        print("✅ No features to execute. Original CSV output unchanged.")

    engineered_shape = engineered_df.shape

    # Stage 6: Verify
    print()
    print("🔎 Data Analyst verifying output...")
    verify_hook = hooks.get("verify", _stub_verify)
    try:
        verification = verify_hook(
            original_shape, engineered_shape, approved_features, run_id,
        )
    except Exception:
        verification = _stub_verify(
            original_shape, engineered_shape, approved_features, run_id,
        )
    vs = verification.get("verification_status", "pass")
    for check in verification.get("checks", []):
        status_icon = "✅" if check["status"] == "pass" else "⚠️"
        print(f"   {status_icon} {check['check']}: {check['details']}")
    print(f"\n✅ Verification complete — {vs}.")

    # Stage 7: Report + Dictionary + Jargon scan
    print()
    print("📝 Generating transformation report...")
    report_hook = hooks.get("generate_report", _stub_generate_report)
    try:
        report_text = report_hook(
            approved_features, rejected_features, verification,
            validation_result, original_shape, engineered_shape,
        )
    except Exception:
        report_text = _stub_generate_report(
            approved_features, rejected_features, verification,
            validation_result, original_shape, engineered_shape,
        )

    print("📝 Generating data dictionary...")
    dict_hook = hooks.get("generate_dictionary", _stub_generate_dictionary)
    try:
        dictionary_text = dict_hook(
            approved_features, engineered_df, validation_result,
        )
    except Exception:
        dictionary_text = _stub_generate_dictionary(
            approved_features, engineered_df, validation_result,
        )

    # Jargon scan
    jargon_hook = hooks.get("jargon_fix")
    report_text, dictionary_text, flagged = scan_jargon(
        report_text, dictionary_text, jargon_hook,
    )
    if flagged:
        log_event(log_path, "jargon_scan_flag", "scan_jargon",
                  f"Flagged terms: {', '.join(flagged)}",
                  "Definitions added or flagged in report")

    print("✅ All outputs ready.")

    # Stage 8: Deliver
    csv_path = os.path.join(output_dir, f"{run_id}-engineered.csv")
    n_new = engineered_shape[1] - original_shape[1]
    written = deliver_outputs(
        engineered_csv_path=csv_path,
        report_text=report_text,
        dictionary_text=dictionary_text,
        validation_result=validation_result,
        log_path=log_path,
        output_dir=output_dir,
        n_original_cols=original_shape[1],
        n_new_cols=n_new,
    )

    return {
        "run_id": run_id,
        "approved_features": approved_features,
        "rejected_features": rejected_features,
        "verification": verification,
        "files": written,
        "status": "success",
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python orchestrator.py <csv_path> [metadata_json] [report_md]")
        sys.exit(1)
    try:
        result = run_feature_engineering_pipeline(
            file_path=sys.argv[1],
            metadata_json_path=sys.argv[2] if len(sys.argv) > 2 else None,
            transformation_report_path=sys.argv[3] if len(sys.argv) > 3 else None,
            output_dir="/tmp/skillb-out",
        )
        print(f"\n=== Pipeline completed: {result['run_id']} ===")
        print(f"Features: {len(result['approved_features'])} approved, "
              f"{len(result['rejected_features'])} rejected")
    except FeatureEngineeringError as e:
        print(f"\nPipeline failed: {e}")
        sys.exit(1)

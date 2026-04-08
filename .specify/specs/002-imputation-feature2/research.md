# Data Transformation with Persona Validation — Phase 0 Research

**Date**: 2026-04-08 | **Spec**: Feature 002 — Data Transformation | **Status**: Approved

---

## Purpose

This document identifies all open technical questions that must be resolved before design begins. For each question, it states the options and recommends an answer with rationale. Approved answers become inputs to Phase 1 (data-model.md, quickstart.md, contracts/).

---

## RQ-001 — Feature 1 Output Consumption Strategy

**Question:** How does Feature 2 read and parse the Feature 1 outputs (NL report markdown + structured profiling JSON)?

**Recommendation:** Two-file consumption with JSON as the primary data source.

The NL report markdown (`{run_id}-summary.md`) is human-readable but fragile to parse programmatically (section headers, free-text). The structured profiling JSON (`{run_id}-profiling-data.json`) contains the same information in machine-readable form (DM-002 validation result, DM-003 quality detections, DM-004 PII scan, DM-006 profiling statistics).

**Approach:**

1. Script checks for both files in the sandbox filesystem. If either is missing → halt with: "No profiling data found. Please run data profiling first."
2. Script loads the JSON file and parses it into Python dicts. This is the authoritative data source for all transformation decisions.
3. The NL report markdown is passed to the LLM as context — the LLM reads it to understand the profiling findings in narrative form, which helps it generate better transformation justifications. But the LLM's transformation proposals must be grounded in the JSON data, not free-text interpretation of the markdown.
4. The original raw CSV is also loaded from the sandbox (A15) for before/after comparison.

**File discovery:** After matching the filename pattern `profile-*-profiling-data.json`, the script validates the JSON contains required top-level keys (`run_id`, `validation_result`, `quality_detections`, `pii_scan`, `profiling_statistics`). If any key is missing → halt with: "Profiling data is incomplete or corrupted. Please re-run data profiling." If multiple matching files exist, Feature 2 uses the most recent by timestamp in the run ID. If ambiguous, Feature 2 asks the user which profiling run to use.

**Key constraint:** The JSON schema is defined by Feature 1's DM-010. Feature 2 must not assume fields beyond what DM-010 specifies.

---

## RQ-002 — Transformation Proposal Architecture

**Question:** How does the LLM generate transformation proposals from the profiling data, and how is the guided catalog enforced?

**Recommendation:** Single LLM call with structured output, catalog embedded in system prompt.

**Phase 1 (Propose):** The LLM receives:

- The structured profiling JSON (quality detections, profiling statistics, PII scan)
- The NL report markdown (for narrative context)
- The guided transformation catalog (embedded in system prompt)
- The fixed 7-step execution order (embedded in system prompt)
- Instructions to produce a structured transformation plan

**System prompt includes the full catalog:**

| Step | Issue Type | Catalog Strategies |
|------|-----------|-------------------|
| 1 | Column name issues | Standardize to snake_case; remove special characters; rename duplicates with numeric suffix |
| 2 | All-missing columns | Drop column |
| 3 | Type inconsistency | Coerce to target type (NaN for failures); parse dates (infer format, fallback to NaT); parse currency/percent (strip symbols, convert to float) |
| 4 | Invalid categories | Map to canonical value; group rare categories into "Other"; flag for human review |
| 5 | Missing values (numeric) | Drop rows; drop column; impute with mean; impute with median; impute with mode; impute with constant |
| 5 | Missing values (categorical) | Drop rows; drop column; impute with mode; impute with "Unknown"; impute with most frequent |
| 6 | Duplicate rows | Drop exact duplicates (keep first); drop exact duplicates (keep last); flag for review |
| 6 | Near-duplicate / conflicting | Keep most recent; keep most complete; flag for human review |
| 7 | Outliers | Cap at percentile (1st/99th); remove rows; flag only (no action); winsorize |

**LLM output format:** A structured list of proposed transformations, one per issue:

```python
{
    "transformations": [
        {
            "step": 1,
            "issue": "string — description of the issue from profiling",
            "affected_columns": ["string"],
            "strategy": "string — from catalog or marked as CUSTOM",
            "is_custom": false,
            "justification": "string — why this strategy",
            "expected_impact": "string — what changes"
        }
    ]
}
```

**Custom strategy handling:** If the LLM proposes a strategy not in the catalog, it must set `is_custom: true` and provide an extended justification explaining why no catalog strategy is appropriate. Custom strategies receive extra scrutiny in the review panel.

**No-issues path:** If the profiling data shows no quality issues (all detections have `status: "clean"`), the LLM proposes an empty transformation list and the pipeline enters the light verification workflow (FR-121).

---

## RQ-003 — Persona Review Panel Implementation

**Question:** How is the two-phase review panel implemented as a single LLM call, and how does it produce structured output including confidence scores?

**Recommendation:** Single LLM call with a multi-perspective system prompt and structured output format.

**Phase 2 (Review) system prompt structure:**

```
You are a review panel of three data experts evaluating proposed
data cleaning transformations. You must adopt three perspectives
simultaneously:

1. CONSERVATIVE VIEW: Challenge whether the proposed strategy
   is the best approach. Question assumptions about data distribution,
   business context, and statistical validity. Look for cases where
   the strategy might introduce bias or lose important information.

2. BUSINESS VIEW: Evaluate whether the proposed strategy makes sense
   for the type of data described. Consider real-world implications —
   would this transformation make sense to a business user? Are there
   domain-specific considerations being missed?

3. TECHNICAL VIEW: Check the mathematical and statistical
   soundness of the proposal. Is the chosen imputation method
   appropriate for the distribution? Is the outlier treatment
   threshold reasonable? Will the transformation preserve important
   statistical properties?

For each proposed transformation, provide:
- A verdict: APPROVE or REJECT
- Reasoning from each perspective (1–2 sentences per perspective)
- If REJECT: a specific alternative recommendation
- A confidence score based on the fixed scoring table
```

**Review panel input:**

- The proposed transformation plan (from Phase 1)
- The profiling statistics (for fact-checking)
- The quality detections (for completeness checking)

**Review panel output format:**

```python
{
    "reviews": [
        {
            "step": 1,
            "issue": "string",
            "verdict": "APPROVE | REJECT",
            "conservative_reasoning": "string",
            "business_reasoning": "string",
            "technical_reasoning": "string",
            "confidence_score": 95,
            "confidence_band": "High",
            "alternative": null,
            "alternative_justification": null
        }
    ],
    "overall_summary": "string — 2–3 sentence summary of panel findings"
}
```

**Fixed confidence scores per band:**

| Panel Outcome | Fixed Score |
|---------------|-------------|
| Unanimous approval, catalog strategy | 95 |
| Unanimous approval, custom strategy | 82 |
| Majority approval with minor dissent | 67 |
| Significant dissent but consensus reached | 50 |
| No consensus | 35 → human review |

**Rejection loop:** Maximum 2 rejection loops **per step** (not per individual transformation). All transformations within a step are proposed and reviewed as a batch.

**Total LLM call budget per pipeline run:**

- Phase 1 proposal: 1 call
- Phase 2 review: 1 call
- Per rejected step: 2 additional calls (re-propose + re-review), max 2 rounds
- Data Analyst verification: 1 call
- Report generation: 1 call
- Jargon fix (if needed): 1 call
- Light verification (no-issues path): 1 call

**Worst case (all 7 steps rejected twice):** 1 + 1 + (7 × 2 × 2) + 1 + 1 + 1 = 33 calls.
**Typical case (0–2 rejections):** 1 + 1 + (2 × 2) + 1 + 1 + 0 = 8 calls.

**No-consensus handling:** If the confidence score is 35 (no consensus) after the review, the transformation is presented to the user with competing options + skip + guidance (FR-122).

---

## RQ-004 — Transformation Execution Engine

**Question:** How are approved transformations executed in the fixed 7-step order, and how is determinism ensured?

**Recommendation:** Script orchestrator with step-specific transformation functions, explicit RNG passing, and before/after metric capture.

**Orchestrator pattern:**

```python
STEP_ORDER = [
    (1, "column_name_standardization", step_1_column_names),
    (2, "drop_all_missing_columns", step_2_drop_missing),
    (3, "type_coercion", step_3_type_coercion),
    (4, "invalid_category_cleanup", step_4_invalid_categories),
    (5, "missing_value_imputation", step_5_imputation),
    (6, "deduplication", step_6_deduplication),
    (7, "outlier_treatment", step_7_outliers),
]

rng = numpy.random.default_rng(42)

for step_num, step_name, step_func in STEP_ORDER:
    approved = get_approved_transformations(step_num, approved_plan)
    if not approved:
        continue
    
    metrics_before = capture_metrics(df)
    df = step_func(df, approved, rng=rng)
    metrics_after = capture_metrics(df)
    
    check_high_impact(metrics_before, metrics_after, thresholds)
    log_step(step_num, step_name, metrics_before, metrics_after)
```

**Determinism guarantees:**

- Explicit RNG: `numpy.random.default_rng(42)` passed to step functions as parameter
- scikit-learn imputers receive `random_state=42` directly
- Pandas sort operations use `sort_values(kind='mergesort')` for stable sort
- Deduplication uses `keep='first'` consistently

**Before/after metric capture function:**

```python
def capture_metrics(df):
    metrics = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "total_missing": int(df.isnull().sum().sum()),
        "total_duplicates": int(df.duplicated().sum()),
        "columns": {}
    }
    for col in df.columns:
        col_metrics = {"dtype": str(df[col].dtype)}
        if pd.api.types.is_numeric_dtype(df[col]):
            col_metrics.update({
                "mean": float(df[col].mean()) if not df[col].isnull().all() else None,
                "min": float(df[col].min()) if not df[col].isnull().all() else None,
                "max": float(df[col].max()) if not df[col].isnull().all() else None,
            })
        elif df[col].dtype == 'category' or df[col].dtype == object:
            col_metrics.update({
                "mode": str(df[col].mode().iloc[0]) if not df[col].isnull().all() else None,
                "unique_count": int(df[col].nunique()),
            })
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            col_metrics.update({
                "min": str(df[col].min()) if not df[col].isnull().all() else None,
                "max": str(df[col].max()) if not df[col].isnull().all() else None,
            })
        elif pd.api.types.is_bool_dtype(df[col]):
            col_metrics.update({
                "true_count": int(df[col].sum()),
                "false_count": int((~df[col]).sum()),
            })
        metrics["columns"][col] = col_metrics
    return metrics
```

**Error handling:** If any step function raises an exception:

1. Pipeline stops immediately — does not produce partial output
2. Error logged to mistake log with step number, transformation type, and error message
3. User sees: "Transformation failed at step {n} ({step_name}): {error}. Please try again in a new session."

---

## RQ-005 — High-Impact Threshold Engine

**Question:** How are the tunable thresholds implemented and checked?

**Recommendation:** Constants dict checked by a post-step comparison function.

```python
HIGH_IMPACT_THRESHOLDS = {
    "row_reduction_pct": 10.0,
    "column_dropped": True,
    "imputation_pct": 30.0,
    "outlier_treatment_pct": 5.0,
    "mean_shift_pct": 15.0,
    "coercion_data_loss": True,
    "category_replacement_pct": 10.0,
}
```

Check function runs after each step. Each flag includes the actual value and the threshold that triggered it, so the transformation report can show explicit context (e.g., "⚠️ 34% of values in column 'region' were imputed — exceeds the 30% threshold for high-impact imputation").

Flags are collected across all steps and passed to: (1) the Data Analyst persona for verification, (2) the transformation report for documentation, (3) the mistake log.

---

## RQ-006 — Transformation Report Generation

**Question:** How is the transformation report structured, and how does the LLM generate it from the execution results?

**Recommendation:** Single LLM call with all execution data as input, producing a structured markdown report.

**Report template:**

```markdown
# Data Transformation Report

**Run ID**: {transform_run_id}
**Source Profiling Run**: {profiling_run_id}
**File**: {original_filename}
**Generated**: {timestamp}

---

## Executive Summary

{2–3 sentence overview of what was done and the overall impact.
 Total transformations applied, rows before/after, columns before/after.}

## Dataset Comparison

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Rows | {n} | {n} | {±n} ({±%}) |
| Columns | {n} | {n} | {±n} |
| Missing cells | {n} ({%}) | {n} ({%}) | {±n} |
| Duplicate rows | {n} ({%}) | {n} ({%}) | {±n} |

## Transformations Applied

### Step {n}: {Step Name}

**{Transformation title}** (Confidence: {score}/100 — {band})

- **What was done**: {description}
- **Why**: {justification referencing profiling findings}
- **Impact**: {before/after metrics for affected columns}

{If high-impact flag}: ⚠️ {flag message with threshold}

**Affected columns:**

| Column | Metric | Before | After |
|--------|--------|--------|-------|
| {col} | {metric} | {val} | {val} |

---

## Rejected Transformations

| Step | Proposed Strategy | Reason for Rejection | Alternative Adopted |
|------|------------------|---------------------|-------------------|
| {n} | {strategy} | {reason} | {alternative} |

## Skipped Transformations

{Any transformations deferred due to no consensus + user chose skip.}

## High-Impact Summary

{All flags collected across all steps, with explanations.}

## Next Steps — Recommended Additional Processing

{Transformations outside Skill A scope: normalization, encoding.
 Lists relevant columns and recommended approaches.
 Reframed: "The following transformations are recommended for the
 next stage of data preparation (feature engineering). They are
 outside the scope of data cleaning but may improve your dataset
 for analysis and modeling."}

## Verification Summary

**Corrections Made:**
- {list, or "None"}

**Confirmed Accurate:**
- {list of verified claims}

**Review Status:** PASS / CORRECTIONS APPLIED

## Pipeline Log Summary

Mistake log written to: {run_id}-mistake-log.json
{Count of entries by type: n rejections, n warnings, n flags.}
```

**LLM prompt constraints:**

- Follow the template exactly — do not add, remove, or reorder sections
- All metrics must come from the script-captured before/after data — do not compute or estimate statistics
- Every transformation must follow the 3-part what/why/impact template
- Plain language (FR-119): basic statistical terms permitted; method-specific terms explained on first use; all acronyms defined
- Do not reproduce raw data values (FR-118 compliance)
- High-impact flags must include the threshold that triggered them
- Next Steps section must reference the Skill A/B boundary decision

---

## RQ-007 — Data Analyst Persona Verification

**Question:** How does the Data Analyst persona verify the final output, and what does it compare?

**Recommendation:** Single LLM call with the original raw CSV summary, the cleaned CSV summary, the approved plan, and the before/after metrics.

**Key distinction from Feature 1:** Feature 1's persona verified that the NL report accurately described the profiling output (text accuracy check). Feature 2's persona verifies that the transformations were applied correctly (data integrity check).

**Verification inputs:**

- Original raw CSV: summary statistics (from Feature 1's profiling JSON — not re-computed)
- Cleaned CSV: summary statistics (from the final `capture_metrics()` call)
- Approved transformation plan with expected outcomes
- Before/after metrics from each step
- High-impact flags

**Verification checklist:**

| Check | What the Analyst Verifies |
|-------|--------------------------|
| Row count consistency | Final row count matches expected count after all approved removals |
| Column count consistency | Final column count matches expected count after drops |
| No unapproved changes | Columns not targeted by any transformation have identical statistics before and after |
| Transformation accuracy | Each transformation's before/after metrics are consistent with the approved strategy |
| No new missing values | Transformations did not introduce unexpected NaN values |
| No new duplicates | Transformations did not introduce duplicate rows |
| High-impact review | Each high-impact flag is acknowledged and justified |
| Type consistency | All columns have the expected dtype after transformation |

**Verification output:** Appended to the transformation report as the Verification Summary section.

**Failure handling:** If the persona detects an issue it cannot resolve (e.g., row count doesn't match expected), the pipeline flags the issue to the user rather than attempting a fix: "⚠️ Verification found a discrepancy: {description}. Please review the transformation report and consider re-running the pipeline."

---

## RQ-008 — Jargon Scan Implementation

**Question:** How does the hybrid jargon scan (script + persona) work in practice?

**Recommendation:** Script regex scan runs on the final report after persona verification. Flagged terms trigger a targeted LLM fix call only if violations are found.

**Script scan logic:**

```python
import re

ACRONYM_WHITELIST = {
    "CSV", "HTML", "JSON", "NaN", "PII", "ID", "LLM", "NL",
    "ASCII", "UTC", "ISO", "PDF", "API"
}

def scan_jargon(report_text):
    acronyms = set(re.findall(r'\b[A-Z]{2,}\b', report_text))
    undefined = acronyms - ACRONYM_WHITELIST
    
    truly_undefined = []
    for acronym in undefined:
        definition_pattern = rf'(\b\w[\w\s]{{2,}}\s*\({acronym}\))|({acronym}\s*\([\w\s]{{3,}}\))'
        if not re.search(definition_pattern, report_text):
            truly_undefined.append(acronym)
    
    return truly_undefined
```

**Workflow:**

1. Persona verification completes → Verification Summary appended to report
2. Script jargon scan runs on the full report
3. If no undefined terms → done, report is final
4. If undefined terms found → one targeted LLM call to define or replace them
5. Script applies corrections to the report
6. No second scan — one pass is sufficient

The persona verification step (RQ-007) already checks for unexplained method-specific terms as part of its plain-language check. The script scan catches what the persona might miss (acronyms are easier to detect programmatically).

---

## RQ-009 — Mistake Log Collection and Writing

**Question:** How are mistake log entries collected during execution and written at the end?

**Recommendation:** In-memory list, written to JSON file at pipeline completion or on error.

**Collection pattern:**

```python
mistake_log = {
    "run_id": transform_run_id,
    "feature": "002-data-transformation",
    "timestamp": iso_timestamp,
    "entries": []
}
```

**Entry types:**

| Type | When Recorded |
|------|--------------|
| `persona_rejection` | A transformation is rejected during the review panel |
| `execution_error` | A step function raises an exception (pipeline halts after logging) |
| `edge_case_warning` | An edge case is detected (e.g., no-issues dataset, high-impact threshold triggered) |
| `consensus_failure` | Confidence score < 50; human review escalated |
| `high_impact_flag` | A threshold is exceeded |
| `human_review_decision` | User chose an option or skipped during escalation |

**Writing:** The mistake log is written in a `try/finally` block so it is persisted even if the pipeline halts on an execution error:

```python
try:
    # ... pipeline execution ...
finally:
    write_mistake_log(mistake_log, transform_run_id)
```

**Privacy:** The `affected_columns` field contains column names only — never raw data values. The `description` and `resolution` fields use generic descriptions, not data samples.

---

## RQ-010 — Human Review Escalation UX

**Question:** How is the human review escalation presented in Claude.ai's conversational interface?

**Recommendation:** Inline presentation with numbered options, simplified perspective labels, and natural language response handling.

**Presentation format (when confidence = 35):**

```
⚠️ The review panel could not reach consensus on how to handle
   {issue description} in column "{column_name}".

   Perspectives:
   • Conservative view: {1-sentence reasoning}
   • Business view: {1-sentence reasoning}
   • Technical view: {1-sentence reasoning}

   Option 1: {Strategy A} (score: {n})
   — {1-sentence justification}
   
   Option 2: {Strategy B} (score: {n})
   — {1-sentence justification}
   
   Option 3: Skip this transformation
   — Column remains as-is; documented as unresolved
   
   Which would you prefer? You can pick a number, type "skip",
   or provide additional guidance.
```

**Response handling:**

- User types "1", "2", or "3" → pipeline applies that choice
- User types "skip" → recorded as skipped, pipeline continues
- User types natural language guidance → LLM incorporates guidance, re-runs Phase 1 for that transformation, then Phase 2. If still no consensus after guidance, the highest-scoring option is adopted with a note: "Adopted based on user guidance; review panel dissent noted."

**Pipeline pause/resume:** The pipeline pauses at the escalation point and waits for user input. All in-memory state (DataFrame, metrics, logs) is preserved in the Python session.

---

## Open Questions Deferred to Phase 1

| ID | Question | Deferred To |
|----|----------|-------------|
| D1 | Exact schema for the transformation plan (LLM output from Phase 1 proposal) | data-model.md |
| D2 | Exact schema for the review panel output | data-model.md |
| D3 | Transformation report field order within each section | data-model.md |
| D4 | Per-step transformation function signatures and parameters | contracts/ |
| D5 | Exact invocation syntax for user transitioning from Feature 1 to Feature 2 | quickstart.md |
| D6 | How skipped transformations interact with downstream steps (dependency-aware skip logic) | contracts/ |

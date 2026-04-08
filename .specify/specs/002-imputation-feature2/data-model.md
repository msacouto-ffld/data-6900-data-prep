# Data Transformation with Persona Validation — Phase 1 Data Model

**Date**: 2026-04-08 | **Spec**: Feature 002 — Data Transformation | **Status**: Approved

---

## Purpose

This document defines all data schemas used by the Data Transformation pipeline. Every field name, type, and required/optional designation is concrete — no placeholders. These schemas are the authoritative source for script contracts, LLM prompt design, and evaluation fixtures.

---

## DM-101 — Feature 1 Inputs (Consumed)

Feature 2 consumes two artifacts produced by Feature 1. These schemas are defined in Feature 1's data model (DM-008, DM-010) and reproduced here for reference only — Feature 2 must not modify them.

**NL Report Markdown** (`{profiling_run_id}-summary.md`)

- Format: Markdown
- Sections consumed by Feature 2: Key Findings, Column-Level Summary, Recommendations, PII Scan Results
- Sections not consumed: Dataset Overview, Statistical Limitations, Verification Summary

**Structured Profiling JSON** (`{profiling_run_id}-profiling-data.json`)

- Format: JSON
- Required top-level keys (validated on load):

```python
{
    "run_id": "string — profile-YYYYMMDD-HHMMSS-XXXX",
    "filename": "string",
    "validated_at": "string — ISO 8601",
    "profiling_mode": "string — full | minimal",
    "validation_result": { /* DM-002 */ },
    "quality_detections": [ /* DM-003 */ ],
    "pii_scan": [ /* DM-004 */ ],
    "profiling_statistics": { /* DM-006 */ }
}
```

**Original Raw CSV** — also loaded from the sandbox for before/after comparison (A15).

---

## DM-102 — Transformation Run Metadata (Internal)

Format: Python dict (in-memory; not written to disk until pipeline completion)
Produced by: Pipeline initialization
Consumed by: All downstream pipeline steps

```python
{
    "transform_run_id": "string — transform-YYYYMMDD-HHMMSS-XXXX",
    "source_profiling_run_id": "string — from DM-101 JSON",
    "original_filename": "string — from DM-101 JSON",
    "original_file_path": "string — sandbox path to raw CSV",
    "started_at": "string — ISO 8601",
    "random_seed": 42,
    "pipeline_version": "1.0"
}
```

Notes:

- `transform_run_id` follows the same hybrid format as Feature 1 but with `transform-` prefix
- `random_seed` is recorded for reproducibility documentation
- `pipeline_version` tracks the execution order version for future compatibility

---

## DM-103 — Transformation Catalog (Static Configuration)

Format: Python dict (hardcoded in system prompt and script)
Purpose: Defines the approved strategies the LLM should prefer

```python
TRANSFORMATION_CATALOG = {
    1: {
        "step_name": "column_name_standardization",
        "strategies": [
            "standardize_to_snake_case",
            "remove_special_characters",
            "rename_duplicates_with_suffix"
        ]
    },
    2: {
        "step_name": "drop_all_missing_columns",
        "strategies": [
            "drop_column"
        ]
    },
    3: {
        "step_name": "type_coercion",
        "strategies": [
            "coerce_to_target_type",
            "parse_dates_infer_format",
            "parse_currency_strip_symbols",
            "parse_percent_to_float"
        ]
    },
    4: {
        "step_name": "invalid_category_cleanup",
        "strategies": [
            "map_to_canonical_value",
            "group_rare_into_other",
            "flag_for_human_review"
        ]
    },
    5: {
        "step_name": "missing_value_imputation",
        "strategies": [
            "drop_rows",
            "drop_column",
            "impute_mean",
            "impute_median",
            "impute_mode",
            "impute_constant",
            "impute_most_frequent",
            "impute_unknown"
        ]
    },
    6: {
        "step_name": "deduplication",
        "strategies": [
            "drop_exact_keep_first",
            "drop_exact_keep_last",
            "keep_most_recent",
            "keep_most_complete",
            "flag_for_human_review"
        ]
    },
    7: {
        "step_name": "outlier_treatment",
        "strategies": [
            "cap_at_percentile",
            "remove_rows",
            "flag_only",
            "winsorize"
        ]
    }
}
```

---

## DM-104 — Transformation Plan (LLM Output — Phase 1 Propose)

Format: Python dict (parsed from LLM JSON output)
Produced by: LLM Phase 1 proposal call
Consumed by: Persona review panel, execution engine

```python
{
    "plan_id": "string — {transform_run_id}-plan",
    "source_profiling_run_id": "string",
    "no_issues_detected": "boolean — true if all quality detections are clean",
    "transformations": [
        {
            "id": "string — t-{step}-{sequence} (e.g., t-5-01, t-5-02)",
            "step": "integer — 1 through 7",
            "step_name": "string — from catalog",
            "issue": "string — {check_type}: {description} (e.g., 'mixed_types: Column zip_code contains both integer and string values')",
            "affected_columns": ["string — column names"],
            "strategy": "string — strategy name from catalog, or free-text if custom",
            "is_custom": "boolean",
            "justification": "string — why this strategy was chosen",
            "expected_impact": "string — what the transformation will change",
            "parameters": {
                "/* strategy-specific — see parameter table below */": ""
            }
        }
    ]
}
```

**Required parameters per strategy:**

| Strategy | Required Parameters | Optional Parameters |
|----------|-------------------|-------------------|
| `coerce_to_target_type` | `target_type` | — |
| `parse_dates_infer_format` | — | `date_format` (if explicit format known) |
| `parse_currency_strip_symbols` | — | `currency_symbol` (default: "$") |
| `parse_percent_to_float` | — | — |
| `impute_mean` | — | — |
| `impute_median` | — | — |
| `impute_mode` | — | — |
| `impute_constant` | `fill_value` | — |
| `impute_unknown` | — | `fill_value` (default: "Unknown") |
| `cap_at_percentile` | `percentile_lower`, `percentile_upper` | — |
| `winsorize` | `percentile_lower`, `percentile_upper` | — |
| `drop_exact_keep_first` | — | — |
| `drop_exact_keep_last` | — | — |
| `map_to_canonical_value` | `canonical_mapping` | — |
| `group_rare_into_other` | `threshold_pct` | — |

The execution engine validates that required parameters are present before running each step. Missing required parameters → halt with error.

Notes:

- Each transformation has a unique `id` for tracking through the review and execution pipeline
- `issue` field must include the structured detection type from DM-003 as a prefix
- `no_issues_detected: true` triggers the light verification workflow (FR-121)
- Transformations are grouped by step but may have multiple entries per step

---

## DM-105 — Review Panel Output (LLM Output — Phase 2 Review)

Format: Python dict (parsed from LLM JSON output)
Produced by: LLM Phase 2 review panel call
Consumed by: Execution engine (for approved transformations), report generator (for rejections), mistake log

```python
{
    "review_id": "string — {transform_run_id}-review-{round}",
    "round": "integer — 1 (initial), 2 or 3 (re-review after rejection)",
    "reviews": [
        {
            "transformation_id": "string — matches DM-104 id",
            "step": "integer",
            "verdict": "string — APPROVE | REJECT",
            "conservative_reasoning": "string — 1–2 sentences",
            "business_reasoning": "string — 1–2 sentences",
            "technical_reasoning": "string — 1–2 sentences",
            "confidence_score": "integer — fixed value: 95, 82, 67, 50, or 35",
            "confidence_band": "string — High | Medium | Low",
            "alternative": "string | null — suggested alternative if REJECT",
            "alternative_justification": "string | null — why the alternative is better"
        }
    ],
    "overall_summary": "string — 2–3 sentence summary of panel findings"
}
```

**Score-to-band mapping:**

| Fixed Score | Band | Behavior |
|-------------|------|----------|
| 95 | High | Proceed automatically |
| 82 | High | Proceed automatically |
| 67 | Medium | Proceed but flag prominently in report |
| 50 | Medium | Proceed but flag prominently in report |
| 35 | Low | Human review escalation (FR-122) |

---

## DM-106 — Approved Transformation Plan (Internal)

Format: Python dict (in-memory)
Produced by: Merging DM-104 and DM-105 after review
Consumed by: Execution engine

```python
{
    "approved_transformations": [
        {
            "id": "string — from DM-104",
            "step": "integer",
            "step_name": "string",
            "strategy": "string",
            "is_custom": "boolean",
            "affected_columns": ["string"],
            "parameters": { /* from DM-104 */ },
            "confidence_score": "integer — from DM-105",
            "confidence_band": "string",
            "review_round": "integer — which round approved it"
        }
    ],
    "rejected_transformations": [
        {
            "id": "string",
            "step": "integer",
            "original_strategy": "string",
            "rejection_reason": "string — from DM-105",
            "alternative_adopted": "string — the strategy that replaced it"
        }
    ],
    "skipped_transformations": [
        {
            "id": "string",
            "step": "integer",
            "issue": "string",
            "reason": "string — no_consensus_user_skipped | no_consensus_user_guided",
            "user_input": "string | null — what the user said, if guidance"
        }
    ],
    "human_review_decisions": [
        {
            "id": "string",
            "step": "integer",
            "options_presented": ["string"],
            "user_choice": "string — option chosen, skip, or guidance text",
            "final_strategy": "string | null — null if skipped"
        }
    ],
    "dependency_warnings": [
        {
            "skipped_step": "integer — the step that was skipped",
            "dependent_step": "integer — the step that depends on it",
            "warning": "string — e.g., 'Skipping type coercion (step 3) may cause incorrect results in imputation (step 5) if columns have mixed types.'"
        }
    ]
}
```

**Step dependency map (hardcoded):**

| Step | Depends On |
|------|-----------|
| 3 (type coercion) | 1 (column names — for correct column references) |
| 4 (invalid categories) | 3 (types — categories must be string type) |
| 5 (imputation) | 3 (types — imputation strategy depends on column type) |
| 6 (deduplication) | 5 (imputation — so imputed values are considered in matching) |
| 7 (outliers) | 3, 5 (types and imputed values — for correct statistical computation) |

If a user skips a step that has dependents, the pipeline issues a warning: "⚠️ Skipping {step_name} may affect the accuracy of {dependent_step_name}. Proceeding with caution." The warning is recorded in the mistake log and included in the transformation report.

---

## DM-107 — Step Execution Result (Internal)

Format: Python dict (one per executed step; collected in list)
Produced by: Each step function in the execution engine
Consumed by: Report generator, Data Analyst persona, mistake log

```python
{
    "step": "integer",
    "step_name": "string",
    "transformations_applied": [
        {
            "id": "string — from DM-106",
            "strategy": "string",
            "affected_columns": ["string"],
            "parameters": { /* from DM-106 */ }
        }
    ],
    "metrics_before": { /* capture_metrics() output — dataset-level + affected columns only */ },
    "metrics_after": { /* capture_metrics() output — dataset-level + affected columns only */ },
    "high_impact_flags": [
        {
            "type": "string — high_impact_flag",
            "condition": "string — row_reduction | column_dropped | imputation_pct | outlier_treatment_pct | mean_shift | coercion_data_loss | category_replacement",
            "value": "float — actual value",
            "threshold": "float — threshold that triggered the flag",
            "message": "string — human-readable flag message",
            "affected_columns": ["string"]
        }
    ],
    "skipped": "boolean — true if this step was skipped (no approved transformations)"
}
```

Note: `metrics_before` and `metrics_after` capture dataset-level metrics (row count, column count, total missing, total duplicates) for all steps, but column-level metrics only for `affected_columns` plus any columns with high-impact flags. This keeps the data structure manageable for wide datasets.

---

## DM-108 — High-Impact Thresholds (Static Configuration)

Format: Python dict (hardcoded constants)
Purpose: Defines tunable default thresholds for flagging high-impact transformations

```python
HIGH_IMPACT_THRESHOLDS = {
    "row_reduction_pct": 10.0,
    "column_dropped": True,
    "imputation_pct": 30.0,
    "outlier_treatment_pct": 5.0,
    "mean_shift_pct": 15.0,
    "coercion_data_loss": True,
    "category_replacement_pct": 10.0
}
```

Each threshold is documented in the report when triggered, showing both the actual value and the threshold.

---

## DM-109 — Transformation Report (Output)

Format: Markdown
Filename: `{transform_run_id}-transform-report.md`
Delivered: Inline in chat + available for download

**Sections (in order):**

1. **Header** — run ID, source profiling run, filename, timestamp
2. **Executive Summary** — 2–3 sentence overview
3. **Dataset Comparison** — table: row count, column count, missing cells, duplicate rows (before/after/change)
4. **Transformations Applied** — per step, per transformation: 3-part template (what/why/impact), confidence score and band, before/after column metrics table, high-impact flags
5. **Rejected Transformations** — table of rejected strategies with reasons and alternatives *(omitted if none)*
6. **Skipped Transformations** — no-consensus transformations the user chose to skip *(omitted if none)*
7. **High-Impact Summary** — all flags across all steps *(omitted if none)*
8. **Next Steps — Recommended Additional Processing** — normalization, encoding deferred to Skill B
9. **Verification Summary** — corrections made, confirmed accurate, review status
10. **Pipeline Log Summary** — pointer to mistake log JSON, entry counts by type

Sections with no content (Rejected Transformations, Skipped Transformations, High-Impact Summary) are omitted entirely to keep the report concise.

**LLM prompt constraints for report generation:**

- Follow template exactly
- All metrics from script-captured data only — no LLM estimates
- 3-part what/why/impact for every transformation
- Plain language (FR-119 compliance)
- No raw data values (FR-118)
- High-impact flags include threshold context
- Method-specific terms explained on first use
- All acronyms defined on first use

---

## DM-110 — Transformation Metadata JSON (Output — Skill B Handoff)

Format: JSON
Filename: `{transform_run_id}-transform-metadata.json`
Delivered: Available for download; consumed by Skill B for handoff validation

```python
{
    "run_id": "string — transform-YYYYMMDD-HHMMSS-XXXX",
    "source_profiling_run_id": "string — profile-YYYYMMDD-HHMMSS-XXXX",
    "original_filename": "string",
    "produced_by": "skill_a",
    "pipeline_version": "string — from DM-102",
    "row_count_before": "integer",
    "row_count_after": "integer",
    "column_count_before": "integer",
    "column_count_after": "integer",
    "columns": {
        "{column_name}": {
            "original_name": "string — pre-standardization name",
            "type": "string — final dtype",
            "transformations_applied": ["string — list of transformation types"]
        }
    },
    "transformations": [
        {
            "step": "integer",
            "type": "string",
            "description": "string",
            "affected_columns": ["string"],
            "confidence_score": "integer"
        }
    ],
    "pii_warnings": [
        {
            "column_name": "string",
            "pii_type": "string",
            "pii_category": "string"
        }
    ],
    "skipped_transformations": [
        {
            "type": "string",
            "description": "string — what was deferred and why",
            "relevant_columns": ["string"]
        }
    ],
    "handoff_contract_version": "1.0"
}
```

**Skill B validation logic (what Skill B checks on receipt):**

1. File exists and `produced_by == "skill_a"` → provenance confirmed (FR-201)
2. Cleaned CSV structural checks match metadata counts → integrity (FR-202)
3. Contract guarantees: no duplicate column names, no all-missing columns, consistent types, no exact duplicates
4. Any check fails → Skill B stops and flags
5. Metadata missing entirely → "This CSV was not produced by Skill A."

---

## DM-111 — Cleaned CSV (Output)

Format: CSV
Filename: `{transform_run_id}-cleaned.csv`
Delivered: Available for download; consumed by Skill B

**Guarantees (Skill Handoff Contract):**

- No duplicate column names
- Column names are snake_case, ASCII-only
- Consistent types per column
- No all-missing columns
- Missing values handled (imputed or documented as intentionally retained)
- No exact duplicate rows
- Outliers treated or documented as retained
- Valid tabular CSV with headers

---

## DM-112 — Mistake Log (Output)

Format: JSON
Filename: `{transform_run_id}-mistake-log.json`
Delivered: Available for download; consumed by PM for pattern analysis

```python
{
    "run_id": "string — transform-YYYYMMDD-HHMMSS-XXXX",
    "feature": "002-data-transformation",
    "timestamp": "string — ISO 8601",
    "entries": [
        {
            "type": "string — persona_rejection | execution_error | edge_case_warning | consensus_failure | high_impact_flag | human_review_decision",
            "step": "integer — 1 through 7, or 0 for pipeline-level events",
            "transformation_type": "string — e.g., missing_value_imputation",
            "description": "string — what happened",
            "resolution": "string — what was done about it",
            "affected_columns": ["string — column names only, no raw data"],
            "confidence_score": "integer | null"
        }
    ]
}
```

**Step 0 events (pipeline-level):**

| Event | Description |
|-------|------------|
| Feature 1 output validation failure | JSON missing or malformed |
| No-issues path triggered | All detections clean; light verification initiated |
| Pipeline initialization error | Run ID generation or file loading failure |
| Report generation failure | LLM failed to produce report |
| Jargon scan violation | Undefined terms found and corrected |

Privacy: `affected_columns` contains column names only — never raw data values. `description` and `resolution` use generic descriptions, not data samples.

---

## DM-113 — Human Review Escalation (Internal — Transient)

Format: Python dict (in-memory; not persisted separately — recorded in DM-106 and DM-112)
Produced by: Pipeline when confidence score = 35
Consumed by: User interaction handler

```python
{
    "escalation_id": "string — {transform_run_id}-esc-{step}",
    "step": "integer",
    "issue": "string",
    "affected_columns": ["string"],
    "column_context": {
        "{column_name}": {
            "type": "string — dtype",
            "missing_pct": "float",
            "unique_count": "integer",
            "role_hint": "string — e.g., 'numeric measure', 'categorical identifier', 'date field'"
        }
    },
    "options": [
        {
            "number": 1,
            "strategy": "string",
            "score": "integer",
            "justification": "string"
        },
        {
            "number": 2,
            "strategy": "string",
            "score": "integer",
            "justification": "string"
        },
        {
            "number": 3,
            "strategy": "skip",
            "score": null,
            "justification": "Column remains as-is; documented as unresolved"
        }
    ],
    "perspectives": {
        "conservative": "string — 1-sentence reasoning",
        "business": "string — 1-sentence reasoning",
        "technical": "string — 1-sentence reasoning"
    },
    "user_response": "string | null — populated after user responds",
    "resolution": "string | null — strategy adopted or 'skipped'"
}
```

The `column_context` provides the user with context about affected columns without revealing raw data values. The `role_hint` is inferred by the LLM from the profiling data.

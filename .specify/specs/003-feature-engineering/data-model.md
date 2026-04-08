# Feature Engineering with Persona Validation — Phase 1 Data Model

**Date**: 2026-04-06 | **Spec**: Feature 003 — Feature Engineering | **Status**: Draft

## Purpose

This document defines all data schemas used by the Skill B pipeline. Every field name, type, and required/optional designation is concrete — no placeholders. These schemas are the authoritative source for script contracts, LLM prompt design, and evaluation fixtures.

---

## DM-001 — Cleaned CSV Input

**Format:** .csv  
**Encoding:** UTF-8  
**Source:** User upload — produced by Skill A or uploaded directly  

**Handoff contract validation rules (FR-201, FR-202):**

| Check | Rule | Gate Type | Failure Message |
|-------|------|-----------|-----------------|
| File parseable | `pd.read_csv()` succeeds | Hard gate | "This file is not a valid CSV. Please check the file format and try again." |
| Has columns | DataFrame has ≥1 column | Hard gate | "This CSV has no columns." |
| Has rows | DataFrame has ≥1 data row | Hard gate | "This CSV contains headers but no data rows." |
| No duplicate column names | `df.columns.duplicated().any()` is False | Hard gate | "Handoff contract violation: duplicate column names found — {list}. Skill A should have resolved this. Please re-run Skill A or fix manually." |
| Clean column names | All columns match `r'^[a-zA-Z_][a-zA-Z0-9_]*$'` | Hard gate | "Handoff contract violation: column names contain special characters — {list}. Skill A should have standardized these." |
| Consistent types | For columns with dtype `object`: `pd.api.types.infer_dtype(col, skipna=True)` does not return "mixed" or "mixed-integer" | Hard gate | "Handoff contract violation: column '{col}' has mixed types. Skill A should have resolved type inconsistencies." |
| Cell count ≤ 500,000 | rows × columns | Hard gate | "This dataset exceeds the feature engineering limit for Claude.ai ({n} cells). Reduce rows or columns." |
| Cell count 100,000–500,000 | rows × columns | Warning | "This dataset is large ({n} cells). Feature engineering may be slow." |
| Missing values | If missing values exist and no Skill A transformation report is available, warn | Soft gate | "Some columns have missing values and no Skill A transformation report was found to explain them. Proceeding — but results may be affected." |

---

## DM-002 — Optional Inputs from Skill A

**These files are read if present, not required. Skill B works without them.**

### profiling-data.json

**Format:** .json  
**Source:** Skill A output (uploaded by user alongside cleaned CSV)  
**What Skill B reads from it:**

```json
{
    "pii_scan": [
        {
            "column_name": "string",
            "pii_type": "string — direct_name | direct_contact | direct_identifier | indirect | financial",
            "pii_category": "string — human-readable",
            "detection_source": "string",
            "confidence": "string — high | medium"
        }
    ],
    "profiling_statistics": {
        "dataset": {
            "n_rows": "integer",
            "n_columns": "integer",
            "types": {
                "numeric": "integer",
                "categorical": "integer",
                "datetime": "integer"
            }
        },
        "columns": {
            "{column_name}": {
                "type": "string",
                "n_missing": "integer",
                "pct_missing": "float",
                "n_unique": "integer",
                "mean": "float | null",
                "std": "float | null",
                "min": "float | null",
                "max": "float | null"
            }
        }
    }
}
```

**Graceful handling:** If the file is present but its schema doesn't match (e.g., Skill A changed its format), Skill B logs a warning and proceeds without it — it does not crash.

### Skill A Transformation Report

**Format:** .md  
**Source:** Skill A output (uploaded by user alongside cleaned CSV)  
**What Skill B reads from it:** The LLM reads the full markdown as context for feature proposals. It helps the LLM understand what cleaning was done — which columns were imputed, what outlier treatment was applied, etc. This context can lead to smarter feature suggestions (e.g., cautious about deriving features from heavily imputed columns).

**Not parsed programmatically** — the LLM reads it as natural language context.

---

## DM-003 — Handoff Validation Result (Internal)

**Format:** Python dict (in-memory)  
**Produced by:** Handoff validation script  
**Consumed by:** All downstream pipeline steps  

```python
{
    "run_id": "string — feature-YYYYMMDD-HHMMSS-XXXX",
    "filename": "string — original uploaded filename",
    "file_path": "string — sandbox path to uploaded file",
    "row_count": "integer",
    "column_count": "integer",
    "cell_count": "integer — row_count × column_count",
    "column_names": ["string — list of all column names"],
    "column_dtypes": {"column_name": "string — pandas dtype"},
    "has_profiling_json": "boolean — whether profiling-data.json was found",
    "has_transformation_report": "boolean — whether Skill A report was found",
    "pii_flags": [
        {
            "column_name": "string",
            "pii_type": "string",
            "source": "string — from_skill_a_json | from_heuristic_scan"
        }
    ],
    "warnings": ["string — list of warning messages issued"],
    "validated_at": "string — ISO 8601 timestamp"
}
```

**Run ID generation:**
```python
import datetime, secrets
now = datetime.datetime.now()
suffix = secrets.token_hex(2)  # 4 hex chars
run_id = f"feature-{now.strftime('%Y%m%d-%H%M%S')}-{suffix}"
```

---

## DM-004 — Dataset Summary for LLM (Internal)

**Format:** Python dict (in-memory)  
**Produced by:** Summary generation script (runs after validation)  
**Consumed by:** LLM for feature proposals and all persona calls  

**Purpose:** A structured summary of the dataset that every LLM call receives. The LLM does not receive the raw CSV — it receives this summary plus sample statistics.

```python
{
    "run_id": "string",
    "filename": "string",
    "row_count": "integer",
    "column_count": "integer",
    "columns": [
        {
            "name": "string",
            "dtype": "string — pandas dtype",
            "n_missing": "integer",
            "pct_missing": "float",
            "n_unique": "integer",
            "is_unique": "boolean — True if all values unique (likely identifier)",
            "sample_values": ["up to 5 non-null values — for LLM context only"],
            "stats": {
                "mean": "float | null — numeric only",
                "std": "float | null",
                "min": "float | null",
                "max": "float | null",
                "median": "float | null"
            },
            "pii_flag": "string | null — PII type if flagged, null if clean"
        }
    ],
    "skill_a_context": "string | null — Skill A transformation report content, if available",
    "profiling_stats": "dict | null — profiling statistics from profiling-data.json, if available"
}
```

**Privacy note:** `sample_values` contains actual data values. This structure is used internally in the Claude.ai session only. The LLM must not reproduce sample values in any output report. PII-flagged columns should have `sample_values` set to `["[PII — values hidden]"]`.

**Known MVP limitation:** For columns not flagged as PII, sample values are visible to the LLM. If Skill A's heuristic scan missed a PII column, the LLM will see those values. This is accepted for MVP because Skill A's thorough two-layer PII scan (heuristic + LLM value inspection) is the primary safeguard. Skill B's lightweight heuristic is the safety net, not the primary detection.

---

## DM-005 — Feature Proposal Batch (Internal)

**Format:** Python dict (in-memory)  
**Produced by:** LLM (one per batch type)  
**Consumed by:** Persona challenge calls  

```json
{
    "batch_number": "integer — 1 through 6",
    "batch_type": "string — datetime_extraction | text_features | aggregations | derived_columns | categorical_encoding | normalization_scaling",
    "proposed_features": [
        {
            "proposed_name": "string — without feat_ prefix (e.g., revenue_per_unit)",
            "description": "string — plain-language description",
            "source_columns": ["string — column names used"],
            "transformation_method": "string — e.g., groupby_transform_sum, one_hot_encode, min_max_scale",
            "benchmark_comparison": "string — why this feature adds value; what you'd lose without it",
            "implementation_hint": "string — pandas/numpy/sklearn code pattern",
            "grouping_key": "string | null — for aggregations only",
            "aggregation_function": "string | null — for aggregations only (sum, mean, count, etc.)",
            "encoding_method": "string | null — for categorical only (one_hot, label)",
            "scaling_method": "string | null — for normalization only (min_max, z_score)"
        }
    ],
    "skipped_reason": "string | null — if this batch type was skipped (e.g., no datetime columns)"
}
```

**If batch is skipped:** `proposed_features` is empty and `skipped_reason` explains why.

**Critical: `implementation_hint` is advisory only.** The execution script never runs LLM-generated code directly. The script reads the structured fields (`transformation_method`, `source_columns`, `grouping_key`, `encoding_method`, `scaling_method`) and executes pre-built, tested code paths that handle edge cases (division by zero, NaN, infinity, empty groups, etc.). The `implementation_hint` helps the script understand the LLM's intent, but the actual implementation is controlled by trusted code — not the LLM.

---

## DM-006 — Persona Challenge Response (Internal)

**Format:** Python dict (in-memory)  
**Produced by:** Each challenge persona LLM call  
**Consumed by:** Pipeline script for confidence scoring and decision tracking  

```json
{
    "persona": "string — feature_relevance_skeptic | statistical_reviewer | domain_expert",
    "batch_number": "integer",
    "reviews": [
        {
            "proposed_name": "string — matches proposed_name from DM-005",
            "approved": "boolean",
            "challenges_raised": [
                {
                    "concern": "string — description of the concern",
                    "severity": "string — minor | substantive",
                    "resolved": "boolean",
                    "resolution": "string | null — how the concern was addressed"
                }
            ],
            "recommendation": "string — approve | reject | modify",
            "modification_suggestion": "string | null — if recommendation is modify, what to change"
        }
    ]
}
```

**The pipeline script parses these responses to:**
- Determine which features are approved, rejected, or need modification
- Count challenges for confidence score assignment
- Log rejections in the mistake log

---

## DM-007 — Approved Feature Set (Internal — Running Tracker)

**Format:** Python list of dicts (in-memory, updated after each batch)  
**Produced by:** Pipeline script after each persona loop completes  
**Consumed by:** Subsequent batch proposal calls (so the LLM knows what's already approved) and the execution script  

```python
[
    {
        "feature_name": "string — with feat_ prefix (e.g., feat_revenue_per_unit)",
        "proposed_name": "string — without prefix (e.g., revenue_per_unit)",
        "batch_number": "integer",
        "batch_type": "string",
        "description": "string",
        "source_columns": ["string"],
        "transformation_method": "string",
        "benchmark_comparison": "string",
        "implementation_hint": "string",
        "confidence_score": "integer — 1 to 5",
        "confidence_justification": "string — e.g., 'All personas approved, no challenges'",
        "challenges_summary": "string — brief summary of any challenges raised and resolved",
        "grouping_key": "string | null",
        "aggregation_function": "string | null",
        "encoding_method": "string | null",
        "scaling_method": "string | null"
    }
]
```

**Confidence score assignment logic (deterministic):**

| Condition | Score |
|-----------|-------|
| 0 challenges raised across all 3 personas | 5 |
| Challenges raised, all resolved, no lingering caveats | 4 |
| Challenges raised, all resolved, with documented caveats | 3 |
| Challenges raised, not all fully resolved | 2 |
| Original rejected, alternative adopted | 1 |

---

## DM-008 — Data Analyst Verification Result (Internal)

**Format:** Python dict (in-memory)  
**Produced by:** Data Analyst persona LLM call (post-execution)  
**Consumed by:** Pipeline script for report generation  

```json
{
    "run_id": "string",
    "verification_status": "string — pass | corrections_applied | issues_found",
    "checks": [
        {
            "check": "string — row_count_preserved | no_unexpected_nan | encoding_correct | original_columns_intact | feat_prefix_applied | no_infinity_values",
            "status": "string — pass | fail | warning",
            "details": "string — description of finding"
        }
    ],
    "corrections": [
        {
            "issue": "string — what was wrong",
            "correction": "string — what was fixed"
        }
    ],
    "confirmed_accurate": ["string — list of verified aspects"]
}
```

**If verification finds issues that cannot be auto-corrected:** The pipeline halts and flags for human review. The mistake log records the issue.

---

## DM-009 — Feature-Engineered CSV (Output)

**Format:** .csv  
**Filename:** `{run_id}-engineered.csv`  
**Encoding:** UTF-8  

**Contents:**
- All original columns from the cleaned CSV (unchanged, same names, same order)
- All approved engineered columns appended after the originals
- Engineered columns prefixed with `feat_`
- Row count matches input exactly (no rows added or removed)
- Row order preserved from input

**Column ordering:**
```
[original_col_1, original_col_2, ..., original_col_N, feat_col_1, feat_col_2, ..., feat_col_M]
```

Original columns in their original order. Engineered columns in execution order (matching the batch sequence: datetime → text → aggregations → derived → encoding → normalization). Within a batch, columns are ordered alphabetically by feature name.

---

## DM-010 — Transformation Report (Output)

**Format:** .md  
**Filename:** `{run_id}-transformation-report.md`  
**Delivered:** Inline in chat + downloadable  

```markdown
# Feature Engineering Transformation Report

**Run ID**: {run_id}
**Input File**: {filename}
**Input Shape**: {rows} rows × {cols} columns
**Output Shape**: {rows} rows × {cols + new_cols} columns ({new_cols} features added)
**Generated**: {timestamp}
**Confidence Score Range**: {min_score}/5 – {max_score}/5

---

## Pipeline Summary

{Brief narrative: how many features proposed, how many approved,
how many rejected, any batches skipped and why.}

## PII Scan Results

{Either:
 - List of PII warnings per column, OR
 - "No potential PII was detected."
 Source noted: "PII flags from Skill A profiling data" or
 "PII flags from Skill B heuristic scan"}

---

## Transformations Applied

### Batch 1: Date/Time Extraction
{If skipped: "Skipped — no datetime columns found in the dataset."}

#### feat_{feature_name}
- **What was done:** {description of the transformation}
- **Why:** {justification — what analytical value it adds}
- **Impact:** {before/after — e.g., "1 new column added; source column
  'order_date' preserved"}
- **Benchmark:** {what you'd gain from this feature and what you'd
  lose without it}
- **Confidence:** {score}/5 — {justification}
- **Source columns:** {list}
- **Method:** {transformation method}

{Repeat for each feature in this batch}

### Batch 2: Text Features
{Same structure as Batch 1}

### Batch 3: Aggregate Features
{Same structure}

### Batch 4: Derived Columns
{Same structure}

### Batch 5: Categorical Encoding
{Same structure}

### Batch 6: Normalization / Scaling
{Same structure}

---

## Rejected Transformations

{For each rejected feature:}
### {proposed_name} (Rejected)
- **What was proposed:** {description}
- **Rejected by:** {persona name}
- **Reason:** {why it was rejected}
- **Alternative considered:** {what was proposed instead, if anything}

---

## Before/After Comparison

| Metric | Before | After |
|--------|--------|-------|
| Row count | {n} | {n} (unchanged) |
| Column count | {original} | {original + new} |
| Engineered features added | — | {count} |
| Features rejected | — | {count} |
| Batches skipped | — | {count} ({reasons}) |

---

## Verification Summary

**Review Status:** {PASS | CORRECTIONS APPLIED | ISSUES FOUND}

**Checks Performed:**
- {list of checks and their status}

**Corrections Made:**
- {list, or "None"}

**Confirmed Accurate:**
- {list of verified aspects}

---

## Jargon Scan

**Terms explained in this report:**
- {list of technical terms and where they are explained}

**Scan status:** {PASS — all terms explained | TERMS FLAGGED — see above}
```

**Column-level summary in Before/After:** If more than 20 features were added, the inline report shows a summary count per batch type. The full feature-by-feature detail is in the downloadable report.

**Inline vs. downloadable version:** When the report has more than 10 features, the inline (chat) version is truncated:
- **Inline version shows:** Pipeline Summary, PII Scan, a summary table of all features (name, type, source columns, confidence score), full detail for the top 5 features by confidence score, Rejected Transformations, Before/After Comparison, and Verification Summary.
- **Inline version note:** "This is a summary. The full transformation report with detailed entries for all {n} features is available in the download: `{run_id}-transformation-report.md`"
- **Downloadable version:** Always contains full detail for every feature, no truncation.

---

## DM-011 — Data Dictionary (Output)

**Format:** .md  
**Filename:** `{run_id}-data-dictionary.md`  
**Delivered:** Inline in chat + downloadable  

```markdown
# Data Dictionary — Engineered Features

**Run ID**: {run_id}
**Input File**: {filename}
**Features Documented**: {count}
**Generated**: {timestamp}

---

## Feature Index

| Feature Name | Type | Source Column(s) | Method |
|-------------|------|-----------------|--------|
| feat_{name} | {dtype} | {sources} | {method} |
| ... | ... | ... | ... |

*Confidence scores for each feature are documented in the transformation report, not repeated here. The data dictionary is a pure reference document for understanding what each feature represents.*

---

## Feature Details

### feat_{feature_name}

- **Description:** {plain-language description of what this feature
  represents — a data scientist should understand it without
  referring to the transformation report}
- **Data type:** {pandas dtype — e.g., float64, int64, object}
- **Source column(s):** {original column names used to derive this feature}
- **Transformation method:** {method — e.g., "one-hot encoding",
  "groupby account_id, sum of net_sale_amount",
  "min-max scaling to 0–1 range"}
- **Value range:** {expected range — e.g., "0 to 1", "0 or 1 (binary)",
  "any positive float"}
- **Missing values:** {count and handling — e.g., "3 NaN values from
  division by zero, replaced with 0"}
- **Notes:** {any additional context — e.g., encoding mappings for
  one-hot: "1 = Premium, 0 = not Premium"}

{Repeat for each engineered feature, in execution order}
```

**Plain language requirement:** A data scientist must be able to read any feature entry and understand it completely without referring to the transformation report or the original dataset (SC-209).

---

## DM-012 — Mistake Log (Output)

**Format:** .md  
**Filename:** `{run_id}-mistake-log.md`  
**Delivery:** Available on request or if errors occurred — not proactively presented  

```markdown
# Mistake Log

**Run ID**: {run_id}
**Generated**: {timestamp}
**Events Logged**: {count}

---

### [{timestamp}] {event_type}

**Step:** {pipeline_step}
**Details:** {description}
**Action Taken:** {what the pipeline did}
**Columns Involved:** {column names — never raw data values}

---

{Repeat for each event}
```

**Event types logged:**

| Event Type | When Logged |
|------------|-------------|
| handoff_contract_violation | Input validation — hard gate failure |
| handoff_contract_warning | Input validation — soft gate warning |
| pii_warning | PII re-check |
| persona_rejection | Challenge loop — feature rejected |
| persona_modification | Challenge loop — feature modified |
| edge_case_triggered | Any step — zero variance, high cardinality, NaN/infinity, etc. |
| execution_error | Transformation execution — error during pandas/sklearn operation |
| verification_correction | Data Analyst review — correction applied |
| verification_issue | Data Analyst review — issue found that could not be auto-corrected |
| jargon_scan_flag | Jargon scan — term flagged and fixed |

**Privacy:** No raw data values ever appear in the log (FR-222). Column names and aggregate statistics are permitted. All identifiers are masked or hashed.

**Append-as-you-go implementation:**
```python
def log_event(log_path, event_type, step, details, action, columns=None):
    timestamp = datetime.datetime.now().isoformat()
    entry = f"\n### [{timestamp}] {event_type}\n\n"
    entry += f"**Step:** {step}\n"
    entry += f"**Details:** {details}\n"
    entry += f"**Action Taken:** {action}\n"
    if columns:
        entry += f"**Columns Involved:** {', '.join(columns)}\n"
    entry += "\n---\n"
    with open(log_path, "a") as f:
        f.write(entry)
```

---

## Open Questions Deferred to Later Phase 1 Files

| ID | Question | Deferred To |
|----|----------|-------------|
| D1 | Exact persona system prompts and checklist content | contracts/ |
| D2 | User invocation syntax and step-by-step walkthrough | quickstart.md |
| D3 | Per-step input/output/error contract details | contracts/ |
| D4 | Evaluation fixtures and pass criteria | contracts/evaluation-suite.md |

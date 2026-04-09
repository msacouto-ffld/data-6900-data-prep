# Feature Engineering with Persona Validation — Phase 1 Contracts

**Date**: 2026-04-06 | **Spec**: Feature 003 — Feature Engineering | **Status**: Draft

---

## contracts/validate-handoff.md

### Contract: validate_handoff
**FR(s):** FR-201, FR-202, FR-219 | **Owner:** Script | **Freedom:** Low | **Runtime:** Executed

### Purpose
Validates the uploaded CSV against the Skill A handoff contract. Generates the run ID. Checks for the three-artifact handoff (CSV + transform-report.md + transform-metadata.json). Verifies provenance and contract version when metadata is present. Produces the validation result dict consumed by all downstream steps. This is the first step in the pipeline.

### Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| file_path | string | Claude.ai upload path (cleaned CSV) | Yes |
| metadata_json_path | string | Claude.ai upload path (transform-metadata.json) | Expected (fallback if absent) |
| transformation_report_path | string | Claude.ai upload path (transform-report.md) | Expected (fallback if absent) |

### Outputs

On success: Returns `validation_result` dict (DM-003 schema).

Console output:
```
🔍 Validating input against Skill A handoff contract...
✅ File: {filename} — valid CSV
✅ Shape: {rows} rows × {cols} columns ({cells} cells)
✅ Provenance: produced by Skill A (contract version 1.0)
✅ Column names: snake_case, no duplicates, no all-missing, no exact duplicate rows
✅ Types: consistent within each column
✅ Run ID: {run_id}
ℹ️ Skill A transform metadata: {found | not found — fallback mode}
ℹ️ Skill A transform report: {found | not found}

All checks passed. Starting feature engineering pipeline...
```

### Validation Rules

| Step | Check | Gate Type | Failure Message |
|------|-------|-----------|-----------------|
| 1 | File exists and is readable | Hard gate | "File not found or not readable." |
| 2 | Parses via `pd.read_csv()` | Hard gate | "This file is not a valid CSV." |
| 3 | ≥1 column | Hard gate | "This CSV has no columns." |
| 4 | ≥1 data row | Hard gate | "This CSV contains headers but no data rows." |
| 5 | Cell count ≤ 500,000 | Hard gate | "This dataset exceeds the feature engineering limit ({n} cells)." |
| 6 | Cell count 100,000–500,000 | Warning | "This dataset is large ({n} cells). Feature engineering may be slow." |
| 7 | Provenance (when metadata present) | Hard gate | "Handoff contract violation: this CSV was not produced by Skill A." |
| 8 | Contract version (when metadata present) | Hard gate | "Handoff contract violation: unsupported contract version '{version}'. Skill B requires 1.0." |
| 9 | No duplicate column names | Hard gate | "Handoff contract violation: duplicate column names — {list}." |
| 10 | Column names snake_case + ASCII | Hard gate | "Handoff contract violation: column names not in snake_case — {list}." |
| 11 | No all-missing columns | Hard gate | "Handoff contract violation: column(s) entirely empty — {list}." |
| 12 | No exact duplicate rows | Hard gate | "Handoff contract violation: exact duplicate rows found ({n} rows)." |
| 13 | Consistent types per column | Hard gate | "Handoff contract violation: column '{col}' has mixed types." |
| 14 | Missing values check | Soft gate | If missing values exist and no metadata available: warn but proceed |
| 15 | transform-metadata.json schema | Informational | If present but malformed: warn and fall back to CSV-only mode |
| 16 | transform-report.md readable | Informational | If present but unreadable: warn and proceed without context |

### Error Conditions

- All hard-gate failures halt the pipeline with an actionable message
- Soft-gate warnings are logged in the mistake log and collected in `validation_result["warnings"]`
- Script must not fail silently

### Dependencies

- pandas — pre-installed
- datetime, secrets, json, re, os — standard library

---

## contracts/scan-pii.md

### Contract: scan_pii
**FR(s):** Constitution PII guardrail (spec gap — added) | **Owner:** Script + LLM | **Freedom:** Medium | **Runtime:** Executed

### Purpose
Checks for PII before feature engineering begins. If transform-metadata.json is available, reads PII flags from its `pii_warnings` field (carried forward by Skill A from Feature 1). If not, runs a lightweight column-name heuristic scan. Produces PII flags consumed by the dataset summary and all LLM calls.

### Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| df | pandas DataFrame | Loaded during validation | Yes |
| validation_result | dict | DM-003 | Yes |

### Outputs

On success: Populates `validation_result["pii_flags"]` (already defined in DM-003).

Console output (from Skill A metadata):
```
🔒 PII scan: loaded {n} flags from Skill A transform metadata
⚠️ Column '{col}' — {PII_type} PII ({category})
...
The LLM will note these columns when proposing features.
```

Console output (heuristic scan):
```
🔒 Running PII scan (heuristic — column names only)...
⚠️ Column '{col}' may contain {PII_type} PII — {category}.
   Consider excluding this column from feature engineering.
...
✅ {n} of {total} columns clear.
```

Console output (no PII):
```
🔒 PII scan complete.
✅ No potential PII detected in this dataset.
```

### Logic

1. Check if `validation_result["has_metadata_json"]` is True
2. If yes: read `pii_warnings` array from transform-metadata.json, populate `pii_flags`
3. If no: run heuristic column-name scan using word-boundary matching against token list (defined in RQ-002)
4. Log all PII warnings to mistake log

### Error Conditions

| Condition | Message |
|-----------|---------|
| transform-metadata.json has invalid pii_warnings schema | "Warning: could not read PII flags from Skill A metadata. Running heuristic scan instead." |

PII scan does not halt the pipeline — findings are warnings only (V1 behavior).

### Dependencies

- pandas — pre-installed
- re — standard library
- json — standard library

---

## contracts/generate-dataset-summary.md

### Contract: generate_dataset_summary
**FR(s):** Supports FR-203, FR-204 | **Owner:** Script | **Freedom:** Low | **Runtime:** Executed

### Purpose
Produces the structured dataset summary (DM-004) that every LLM call receives. The LLM does not analyze the raw CSV directly — it works from this summary. Runs after validation and PII scan.

### Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| df | pandas DataFrame | Loaded during validation | Yes |
| validation_result | dict | DM-003 | Yes |

### Outputs

On success: Returns `dataset_summary` dict (DM-004 schema).

No console output — this is an internal step.

### Logic

1. For each column: compute dtype, missing count/percentage, unique count, is_unique flag
2. For numeric columns: compute mean, std, min, max, median
3. For each column: extract up to 5 non-null sample values via `df[col].dropna().head(5).tolist()`
4. For PII-flagged columns: replace sample_values with `["[PII — values hidden]"]`
5. Attach Skill A transformation report content as `skill_a_context` (string) if available
6. Attach Skill A metadata content as `skill_a_metadata` (dict) if available — provides column transformation history and skipped transformations to inform feature suggestions

### Error Conditions

| Condition | Message |
|-----------|---------|
| DataFrame is empty | "Pipeline error: no data available for summary generation." |

### Dependencies

- pandas — pre-installed
- numpy — pre-installed

---

## contracts/propose-features.md

### Contract: propose_features
**FR(s):** FR-203, FR-204, FR-225 | **Owner:** LLM | **Freedom:** High | **Runtime:** LLM-executed

### Purpose
For each batch type, the LLM analyzes the dataset summary and proposes feature engineering transformations. Each proposal includes a justification and benchmark comparison. Produces a feature proposal batch (DM-005) consumed by the persona challenge loop. Called once per active batch (up to 6 times).

### Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| dataset_summary | dict | DM-004 | Yes |
| batch_type | string | Pipeline orchestration | Yes |
| approved_features_so_far | list | DM-007 (running tracker) | Yes (may be empty for Batch 1) |
| validation_result | dict | DM-003 | Yes |

### Outputs

Returns `feature_proposal_batch` dict (DM-005 schema).

Console output:
```
📋 Batch {n}: {Batch Type Name}
   Analyzing {relevant column type} columns...

   Proposed features:
   1. {name} — from '{source}' — {brief benchmark}
   2. {name} — from '{source}' — {brief benchmark}
   ...
```

If batch is skipped:
```
📋 Batch {n}: {Batch Type Name}
   ℹ️ Skipped — {reason}.
```

### LLM Prompt Constraints

The LLM system prompt must include:

- **Batch focus:** "You are proposing features of type: {batch_type} only. Do not propose features outside this type."
- **Context awareness:** "These features have already been approved in previous batches: {approved_features_so_far}. You may reference them but do not re-propose them."
- **Benchmark required:** "Every proposed feature must include a benchmark comparison: why it adds analytical value and what you'd lose without it."
- **Implementation hint:** "Include an implementation_hint for each feature. This is advisory only — the execution script will use its own tested code, not your hint."
- **PII awareness:** "These columns are flagged for PII: {pii_flags}. Note PII-flagged columns in your proposals. The Domain Expert persona will challenge features derived from PII columns."
- **Aggregate cap:** "For aggregation batches: propose a maximum of 10 features. If more are possible, propose the top 10 by expected value and note the remainder."
- **No-opportunity handling (FR-225):** "If no features of this type are possible, return an empty proposal with a skipped_reason explaining why."

### Error Conditions

| Condition | Message |
|-----------|---------|
| LLM fails to produce a structured proposal | Retry once. If second attempt fails: "Feature proposal failed for Batch {n}. Skipping this batch." |
| LLM proposes features outside the batch type | Caught by pipeline script — out-of-type features are queued for the correct batch (e.g., an encoding suggestion in Batch 3 is queued for Batch 5) with a warning logged |

### Dependencies

- LLM (Claude 4.5 Sonnet)

---

## contracts/challenge-features.md

### Contract: challenge_features
**FR(s):** FR-205, FR-206, FR-207 | **Owner:** LLM | **Freedom:** Medium | **Runtime:** LLM-executed

### Purpose
Three separate LLM calls — one per challenge persona — review the proposed feature batch. Each persona has a narrow checklist and returns a structured response (DM-006). The pipeline script aggregates responses, determines approvals/rejections, and assigns confidence scores (DM-007). On rejection, the LLM proposes an alternative (max 2 rejection cycles per feature).

### Inputs (per persona call)

| Input | Type | Source | Required |
|-------|------|--------|----------|
| feature_proposal_batch | dict | DM-005 | Yes |
| dataset_summary | dict | DM-004 | Yes |
| persona_type | string | Pipeline orchestration | Yes |

### Outputs

Each persona returns a `persona_challenge_response` dict (DM-006 schema).

Console output (per persona):
```
🔎 {Persona Name}: {summary of review}
```

Console output (batch summary):
```
✅ Batch {n} complete: {approved} features approved, {rejected} rejected
   (confidence: {scores})
```

### Persona System Prompts

**Feature Relevance Skeptic:**
```
You are a Feature Relevance Skeptic. Your job is to identify redundant
or low-value features. For each proposed feature, ask:
- Is this feature redundant with an existing column? Check if it would
  be >0.95 correlated with any existing or previously approved feature.
- Does it add information beyond what's already available?
- Would removing it meaningfully reduce analytical capability?

Return your review in this exact JSON format:
{DM-006 schema}
```

**Statistical Reviewer:**
```
You are a Statistical Reviewer. Your job is to verify that proposed
methods are valid for the actual data. For each proposed feature, ask:
- Is the transformation method appropriate for this column's dtype
  and distribution?
- Will this produce valid results? (e.g., normalizing a zero-variance
  column, one-hot encoding 500 categories, scaling with extreme outliers)
- Are there edge cases that would produce NaN, infinity, or errors?

Return your review in this exact JSON format:
{DM-006 schema}
```

**Domain Expert:**
```
You are a Domain Expert. Your job is to evaluate whether proposed
features make business sense. For each proposed feature, ask:
- Would a data scientist working with this type of data actually use this?
- Does the grouping key / aggregation / ratio make real-world sense?
- Could the feature be misleading? (e.g., a ratio where the denominator
  is frequently zero)
- Is the benchmark comparison convincing?

Return your review in this exact JSON format:
{DM-006 schema}
```

### Rejection Cycle Logic

```
For each rejected feature:
  Cycle 1: LLM proposes alternative → 3 personas review
    → If approved: record with confidence score
    → If rejected again:
  Cycle 2: LLM proposes second alternative → 3 personas review
    → If approved: record with confidence score
    → If rejected again: feature dropped, logged in mistake log
```

Maximum: 2 rejection cycles per feature. Maximum additional LLM calls per rejected feature: 2 (proposal) + 6 (3 personas × 2 cycles) = 8.

**Batch-level rejection cap:** If more than 5 features in a single batch are rejected, the remaining rejected features are dropped without retry and logged in the mistake log. This prevents runaway LLM calls on batches where the proposals are fundamentally misaligned with the data.

### Confidence Score Assignment (Deterministic)

After all three personas respond, the pipeline script counts challenges and assigns a fixed value matching Skill A's bands:

| Condition | Score | Band |
|-----------|-------|------|
| 0 challenges raised across all 3 personas | 95 | High |
| Challenges raised, all resolved, no caveats | 82 | High |
| Challenges raised, all resolved, with caveats | 67 | Medium |
| Challenges raised, not all resolved | 50 | Medium |
| Original rejected, alternative adopted | 35 | Low |

### Error Conditions

| Condition | Message |
|-----------|---------|
| Persona fails to return structured response | Retry once. If fails again: treat as "approved with no challenges" and log warning. |
| All three personas reject and no alternative found after 2 cycles | Feature dropped. Logged in mistake log. |

### Dependencies

- LLM (Claude 4.5 Sonnet)

---

## contracts/execute-transformations.md

### Contract: execute_transformations
**FR(s):** FR-208, FR-209, FR-210, FR-211 | **Owner:** Script | **Freedom:** Low | **Runtime:** Executed

### Purpose
Executes all approved feature engineering transformations on the cleaned CSV. Uses only pandas, numpy, and scikit-learn. Produces the feature-engineered CSV (DM-009). Applies transformations in the fixed execution order. Adds the `feat_` prefix to all new columns.

### Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| df | pandas DataFrame | Loaded during validation | Yes |
| approved_features | list | DM-007 | Yes |
| validation_result | dict | DM-003 | Yes |

### Outputs

On success: Returns modified DataFrame with engineered columns appended. Writes `{run_id}-engineered.csv` to sandbox filesystem.

Console output:
```
⚙️ Executing approved transformations...
   Batch 1: Date/Time Extraction — {n} features ✅
   Batch 2: Text Features — {skipped | n features ✅}
   ...
✅ All transformations executed. {total} new features created.
   Output shape: {rows} rows × {cols} columns
```

### Execution Rules

**Order:** Transformations applied in batch order (1→6). Within a batch, features applied in alphabetical order by feature name.

**Prefix:** Script adds `feat_` prefix to every new column name. The LLM never applies the prefix.

**Column preservation (FR-210):** All original columns remain unchanged unless an approved decision explicitly removes one (e.g., dropping the original categorical column after one-hot encoding). The script verifies original columns are intact after each batch.

**Transformation implementations (pre-built, not LLM-generated):**

| transformation_method | Implementation |
|----------------------|----------------|
| extract_day_of_week | `pd.to_datetime(df[col]).dt.dayofweek` |
| extract_hour | `pd.to_datetime(df[col]).dt.hour` |
| extract_month | `pd.to_datetime(df[col]).dt.month` |
| extract_quarter | `pd.to_datetime(df[col]).dt.quarter` |
| text_string_length | `df[col].astype(str).str.len()` |
| text_word_count | `df[col].astype(str).str.split().str.len()` |
| groupby_agg | `df.groupby(key)[col].agg(func).reset_index()` then merge back |
| derived_ratio | `df[col_a] / df[col_b]` with division-by-zero → NaN handling |
| derived_difference | `df[col_a] - df[col_b]` |
| one_hot_encode | `pd.get_dummies(df, columns=[col], prefix='feat_' + name)` — prefix applied directly by get_dummies |
| label_encode | `sklearn.preprocessing.LabelEncoder().fit_transform(df[col])` |
| min_max_scale | `sklearn.preprocessing.MinMaxScaler().fit_transform(df[[col]])` |
| z_score_scale | `sklearn.preprocessing.StandardScaler().fit_transform(df[[col]])` |

**Edge case handling (built into each implementation):**
- Division by zero → NaN, logged in mistake log
- Infinity values → NaN, logged
- NaN from failed datetime parsing → NaN, logged
- Unknown categories during encoding → logged, pipeline continues
- Zero-variance column during scaling → skip scaling, logged

### Error Conditions

| Condition | Message |
|-----------|---------|
| Transformation raises exception | "Execution error in Batch {n}: {error}. Action: {handling}. Logged in mistake log." Pipeline continues with remaining transformations. |
| Critical failure (DataFrame corrupted) | "Critical execution error — pipeline halted. No output CSV produced. See mistake log." |
| No approved features to execute | Proceeds to FR-225 no-opportunity path. |

### Dependencies

- pandas — pre-installed
- numpy — pre-installed
- scikit-learn — pre-installed

---

## contracts/verify-output.md

### Contract: verify_output
**FR(s):** FR-205 (Test step of Verification Ritual) | **Owner:** LLM (Data Analyst persona) | **Freedom:** Medium | **Runtime:** LLM-executed

### Purpose
Post-execution quality gate. The Data Analyst persona compares the feature-engineered output against the cleaned input and the approved feature set. Catches unintended side effects. Produces the verification result (DM-008) used in the transformation report.

### Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| original_df | pandas DataFrame | Cleaned CSV (pre-transformation) | Yes |
| engineered_df | pandas DataFrame | Post-transformation output | Yes |
| approved_features | list | DM-007 | Yes |
| validation_result | dict | DM-003 | Yes |

### Outputs

Returns `verification_result` dict (DM-008 schema).

Console output (pass):
```
🔎 Data Analyst verifying output...
   ✅ Row count preserved
   ✅ Original columns unchanged
   ✅ All engineered columns present with feat_ prefix
   ✅ No unexpected NaN values
   ✅ No infinity values
   ✅ Encoding mappings correct
✅ Verification complete — all checks passed.
```

Console output (corrections):
```
🔎 Data Analyst verifying output...
   ⚠️ {description of issue}
   ✅ Correction: {what was fixed}
✅ Verification complete — {n} correction(s) applied.
```

### Verification Checklist

| Check | What Is Verified |
|-------|-----------------|
| row_count_preserved | `len(engineered_df) == len(original_df)` |
| original_columns_intact | All original column names present with same dtypes and values |
| feat_prefix_applied | All new columns start with `feat_` |
| expected_columns_present | Every feature in approved_features has a corresponding column |
| no_unexpected_nan | No NaN values in engineered columns except where documented (e.g., division by zero handling) |
| no_infinity_values | No infinity values in any engineered column |
| encoding_correct | One-hot encoded columns have only 0/1 values; label encoded columns have expected range |
| scaling_correct | Min-max scaled columns are within [0, 1]; z-score scaled columns have mean ≈ 0, std ≈ 1 |
| no_data_leakage | Engineered columns don't contain information from the target variable (if identifiable) |

### Data Analyst Persona System Prompt

```
You are a Data Analyst performing a quality review. You have two
DataFrames: the original cleaned CSV and the feature-engineered output.
You also have the list of approved features with their specifications.

Your job:
1. Verify every check in the checklist
2. For each check, report pass/fail/warning with specific details
3. If you find an issue that can be corrected (e.g., a missing column,
   an incorrect encoding), describe the correction
4. If you find an issue that cannot be auto-corrected, flag it for
   human review

Return your review in this exact JSON format:
{DM-008 schema}
```

### Error Conditions

| Condition | Message |
|-----------|---------|
| Verification finds uncorrectable issues | "Verification found issues that require human review: {description}. Pipeline halted." |
| Persona fails to return structured response | "Verification could not be completed. Delivering output with disclaimer." |

### Dependencies

- LLM (Claude 4.5 Sonnet)
- pandas — for DataFrame comparison

---

## contracts/scan-jargon.md

### Contract: scan_jargon
**FR(s):** FR-224 | **Owner:** Script | **Freedom:** Low | **Runtime:** Executed

### Purpose
Layer 1 of the jargon scan. A script checks the transformation report and data dictionary for technical terms that require plain-language explanation. Flagged terms are passed to the LLM for rewriting. Layer 2 (the Data Analyst verification persona) catches anything the script misses.

### Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| report_text | string | Generated transformation report | Yes |
| dictionary_text | string | Generated data dictionary | Yes |

### Outputs

On success: Returns list of flagged terms with locations.

Console output:
```
🔍 Running jargon scan...
⚠️ {n} term(s) flagged: {list}
```

Or:
```
🔍 Running jargon scan...
✅ All technical terms are explained.
```

### Term List (MVP)

```python
JARGON_TERMS = [
    "one-hot encoding", "label encoding", "min-max scaling",
    "z-score", "standard deviation", "normalization",
    "standardization", "variance", "cardinality",
    "dimensionality", "dummy variable", "feature extraction",
    "imputation", "interpolation", "ordinal", "nominal",
    "categorical", "continuous", "discrete", "skewness",
    "kurtosis", "correlation", "multicollinearity",
    "outlier detection"
]
```

### Scan Logic

For each term found in the report or dictionary:
1. Search for the term (case-insensitive)
2. Check if a plain-language explanation appears within ~200 words of the term
3. "Explanation" is detected by proximity of phrases like: "which means", "this means", "in other words", "that is", a parenthetical definition, or a sentence starting with the term followed by "is" or "refers to"
4. If no explanation found: flag the term with its location

Flagged terms are passed to the LLM with instruction: "Rewrite the following sections to include a brief, plain-language explanation of each flagged term. Do not change the meaning or structure — only add clarity."

### Error Conditions

Non-blocking — if the scan fails, the pipeline proceeds and relies on the verification persona (Layer 2) to catch jargon.

### Dependencies

- re — standard library

---

## contracts/generate-report.md

### Contract: generate_report
**FR(s):** FR-212, FR-213, FR-214, FR-215, FR-223 | **Owner:** LLM + Script | **Freedom:** Medium | **Runtime:** LLM-executed

### Purpose
Generates the transformation report (DM-010) following the mandatory template. The script provides the structure and data; the LLM writes the narrative content. After generation, the jargon scan runs, then the verification persona reviews.

### Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| approved_features | list | DM-007 | Yes |
| rejected_features | list | Collected during challenge loop | Yes |
| validation_result | dict | DM-003 | Yes |
| verification_result | dict | DM-008 | Yes |
| original_df | pandas DataFrame | Pre-transformation | Yes |
| engineered_df | pandas DataFrame | Post-transformation | Yes |

### Outputs

Returns `transformation_report` string (markdown following DM-010 template).

Console output:
```
📝 Generating transformation report...
✅ Report generated.
```

### LLM Prompt Constraints

- **Template enforcement:** "Follow the DM-010 report template exactly."
- **3-part justification:** "Every feature entry must include: What was done, Why, and Impact."
- **Benchmark included:** "Every feature must include its benchmark comparison."
- **Confidence scores:** "Every feature must show its confidence score with justification."
- **Before/after:** "Include the Before/After comparison table with row count, column count, and features added/rejected/skipped."
- **Rejected features:** "Document every rejected feature with the persona that rejected it and the reason."
- **Plain language (FR-223):** "Write for a non-technical business user. Explain all technical terms on first use."
- **Privacy:** "Never include raw data values in the report."
- **Truncation rule:** "If more than 10 features, generate the full report for download. The inline version shows a summary table plus top 5 features by confidence."

### Error Conditions

| Condition | Message |
|-----------|---------|
| LLM fails to generate report | Retry once. If fails: "Report generation failed. Outputting CSV without report." |

### Dependencies

- LLM (Claude 4.5 Sonnet)
- pandas — for before/after statistics

---

## contracts/generate-dictionary.md

### Contract: generate_dictionary
**FR(s):** FR-217, FR-223 | **Owner:** LLM | **Freedom:** Medium | **Runtime:** LLM-executed

### Purpose
Auto-generates the data dictionary (DM-011) documenting every engineered feature. A data scientist should be able to read any entry and understand the feature completely without referring to other documents (SC-209).

### Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| approved_features | list | DM-007 | Yes |
| engineered_df | pandas DataFrame | Post-transformation | Yes |

### Outputs

Returns `data_dictionary` string (markdown following DM-011 template).

Console output:
```
📝 Generating data dictionary...
✅ Data dictionary generated.
```

### LLM Prompt Constraints

- **Template enforcement:** "Follow the DM-011 template exactly."
- **Self-contained entries:** "Each feature entry must be understandable on its own. A reader should never need to refer to the transformation report or original dataset."
- **Required fields per feature:** Feature name (with `feat_` prefix), plain-language description, data type, source column(s), transformation method, value range, missing value handling, notes.
- **Plain language:** "Explain all technical terms. A data scientist who has never seen this dataset should understand every entry."
- **No raw data values:** "Do not include actual data values — use descriptions of ranges and patterns."

### Error Conditions

| Condition | Message |
|-----------|---------|
| LLM fails to generate dictionary | Retry once. If fails: "Dictionary generation failed. Feature details available in transformation report." |

### Dependencies

- LLM (Claude 4.5 Sonnet)

---

## contracts/deliver-outputs.md

### Contract: deliver_outputs
**FR(s):** FR-218 | **Owner:** Script | **Freedom:** Low | **Runtime:** Executed

### Purpose
Writes all output files to the sandbox filesystem, displays the transformation report and data dictionary inline in chat, and presents files for download.

### Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| engineered_df | pandas DataFrame | Post-transformation | Yes |
| transformation_report | string | From generate_report | Yes |
| data_dictionary | string | From generate_dictionary | Yes |
| validation_result | dict | DM-003 | Yes |
| mistake_log_path | string | Path to running mistake log | Yes |

### Outputs

Files written to sandbox:

| File | Format | Filename |
|------|--------|----------|
| Feature-engineered CSV | .csv | `{run_id}-engineered.csv` |
| Transformation report | .md | `{run_id}-transformation-report.md` |
| Data dictionary | .md | `{run_id}-data-dictionary.md` |
| Mistake log | .md | `{run_id}-mistake-log.md` (already written throughout run) |

**Inline delivery:**
1. Transformation report (truncated if >10 features)
2. Data dictionary

**Download presentation (3 primary files):**
```
📥 Your feature engineering outputs are ready:
   • {run_id}-engineered.csv
     — Feature-engineered dataset ({original} original + {new} new columns)
   • {run_id}-transformation-report.md
     — Full transformation report with all feature details
   • {run_id}-data-dictionary.md
     — Data dictionary for all engineered features

Engineered columns are prefixed with 'feat_' — use
df.filter(like='feat_') to select them.
```

**Mistake log (always shown):**
```
📋 Mistake log for this run:
   • {run_id}-mistake-log.md
```
The mistake log is always presented — it is the complete operational record of the run, including routine persona rejections, warnings, and any errors. This is what the PM uses to identify recurring patterns.

### Error Conditions

| Condition | Message |
|-----------|---------|
| CSV write fails | "Output error: could not save CSV. Please copy the data from the inline report." |
| Report/dictionary write fails | "Output error: could not save {file}. The content has been delivered inline above." |

File write failures are non-blocking for inline delivery.

### Dependencies

- pandas — for CSV export
- json — standard library
- Claude.ai file presentation mechanism

---

## contracts/evaluation-suite.md

### Evaluation Suite: V1 Minimum

**Coverage:** User Stories P1 (1–6) and P2 (7, 8) | **Format:** Structured evaluation cases

### Purpose
Five evaluation cases ensuring Skill B meets the spec's acceptance scenarios and edge-case requirements. Each evaluation defines a fixed input set, invocation, expected behavior, and binary pass criteria.

---

### eval-001 — Handoff Contract Validation (User Story 1)

**Fixed Input Set:** Five separate CSVs, each tested independently:

| CSV | Description | Expected Behavior |
|-----|-------------|-------------------|
| valid-simple.csv | 200 rows × 8 columns, all checks pass, mixed column types | Validation passes, pipeline proceeds |
| bad-duplicate-cols.csv | Has 2 duplicate column names | Hard gate: contract violation message, pipeline stops |
| bad-special-chars.csv | Column names with spaces and $ | Hard gate: contract violation message, pipeline stops |
| bad-mixed-types.csv | One column with mixed int/string | Hard gate: contract violation message, pipeline stops |
| not-a-csv.txt | Plain text file | Hard gate: "not a valid CSV" |

**Pass Criteria:**

| # | Criterion | Pass Condition |
|---|-----------|----------------|
| 1 | Valid CSV accepted | valid-simple.csv passes validation, pipeline proceeds |
| 2 | Duplicate columns caught | Specific violation message names the columns |
| 3 | Special characters caught | Specific violation message names the columns |
| 4 | Mixed types caught | Specific violation message names the column |
| 5 | Non-CSV rejected | Clear error message, no pipeline execution |
| 6 | Error messages actionable | Every message tells the user what to fix |

---

### eval-002 — Full Feature Engineering Pipeline (User Stories 2–6)

**Fixed Input Set:**
- full-pipeline-test.csv: 500 rows × 12 columns, specifically designed with:
  - 2 datetime columns (order_date, ship_date)
  - 3 categorical columns (category: 4 values, region: 8 values, product_type: 50 values)
  - 5 numeric columns (sale_amount, units_sold, unit_price, discount_pct, shipping_cost)
  - 1 identifier column (account_id — repeated values, suitable for groupby)
  - 1 text column (product_description — varying lengths)
  - No PII columns

**Pass Criteria:**

| # | Criterion | Pass Condition |
|---|-----------|----------------|
| 1 | Features proposed | At least one feature proposed per non-skipped batch |
| 2 | Personas challenged | At least one persona challenge raised across all batches |
| 3 | Confidence scores present | Every approved feature has a fixed-value score: 95, 82, 67, 50, or 35 |
| 4 | Execution complete | Output CSV contains all approved features with `feat_` prefix |
| 5 | Original columns preserved | All 12 input columns unchanged in output |
| 6 | Row count preserved | Output has exactly 500 rows |
| 7 | Report generated | Transformation report follows DM-010 template, all sections present |
| 8 | 3-part template | Every feature entry has What/Why/Impact |
| 9 | Benchmarks present | Every feature has a benchmark comparison |
| 10 | Rejected features documented | At least the high-cardinality column (50 categories) triggers a persona challenge |
| 11 | Dictionary generated | Data dictionary follows DM-011 template, entry for every feature |
| 12 | Downloads available | CSV, report, and dictionary all downloadable |
| 13 | Plain language | No undefined technical terms in report or dictionary |
| 14 | No raw data values | Neither report nor dictionary contains actual data values |

---

### eval-003 — PII Detection and Handling

**Fixed Input Set:**
- pii-dataset.csv: 200 rows × 10 columns with:
  - Column `customer_name`: synthetic names (Direct PII)
  - Column `email`: synthetic emails (Direct PII)
  - Column `zip_code`: postal codes (Indirect PII)
  - Column `account_number`: synthetic IDs (Financial PII)
  - Remaining columns: numeric, no PII

**Run A:** Upload CSV + transform-metadata.json (with PII flags carried forward from Skill A)
**Run B:** Upload CSV only (no metadata — fallback mode)

**Pass Criteria:**

| # | Criterion | Pass Condition |
|---|-----------|----------------|
| 1 | Run A loads PII flags | Console shows "loaded {n} flags from Skill A transform metadata" |
| 2 | Run B runs heuristic | Console shows "Running PII scan (heuristic)" |
| 3 | All PII columns flagged | customer_name, email, zip_code, account_number all flagged in both runs |
| 4 | Non-PII columns clear | Remaining 6 columns not flagged |
| 5 | LLM notes PII in proposals | Feature proposals mention PII-flagged columns |
| 6 | Domain Expert challenges PII-derived features | If a feature is proposed from a PII column, Domain Expert raises a concern |
| 7 | No raw PII in outputs | Report and dictionary contain column names only, no actual data values |

---

### eval-004 — No Feature Engineering Opportunities (FR-225)

**Fixed Input Set:**
- Two CSVs tested independently:

| CSV | Description | Expected Path |
|-----|-------------|---------------|
| all-identifiers.csv | 100 rows × 3 columns, all unique values | Fast-path — skip persona loop |
| ambiguous-data.csv | 100 rows × 5 columns, mostly identifiers but 1 numeric column | Standard path — persona loop confirms no opportunities |

**Pass Criteria:**

| # | Criterion | Pass Condition |
|---|-----------|----------------|
| 1 | Fast-path triggers | all-identifiers.csv skips persona loop |
| 2 | Standard path runs | ambiguous-data.csv goes through persona loop |
| 3 | Output CSV unchanged | Output is identical to input in both cases |
| 4 | Report explains why | Transformation report contains "no feature engineering opportunities" with specific reason |
| 5 | Data dictionary empty or states no features | Dictionary notes no features were created |
| 6 | Run ID present | Both outputs have valid run IDs |

---

### eval-005 — Edge Cases and Error Handling

**Fixed Input Set:** Individual test cases:

| Test Case | Input | Expected Behavior |
|-----------|-------|-------------------|
| High-cardinality one-hot | CSV with a 500-category column | Persona challenges one-hot encoding; suggests alternative (frequency/label encoding) |
| Zero-variance column | CSV with a column where all values = 42 | Pipeline skips normalization for that column; documents reason |
| Division by zero | CSV where a ratio denominator column has zeros | Execution replaces with NaN; logged in mistake log; documented in report |
| Column explosion | CSV where one-hot encoding would create 100+ columns | FR-216: flagged in report; persona challenges whether it's justified |
| NaN in derived feature | CSV where a date column has unparseable values | Date extraction produces NaN for those rows; logged and documented |

**Pass Criteria:**

| # | Criterion | Pass Condition |
|---|-----------|----------------|
| 1 | High cardinality challenged | Persona rejects or modifies the one-hot proposal |
| 2 | Zero variance handled | Normalization skipped with documented reason |
| 3 | Division by zero handled | NaN replacement, logged, documented |
| 4 | Column explosion flagged | Report and personas flag the dimensionality increase |
| 5 | NaN documented | Missing values from failed parsing are documented |
| 6 | No pipeline crashes | All edge cases handled gracefully — no unhandled exceptions |
| 7 | Mistake log captures events | Each edge case produces at least one mistake log entry |

---

### Evaluation Fixture Files

The following synthetic files must be created before evaluations run:

| File | Purpose |
|------|---------|
| valid-simple.csv | eval-001 (valid CSV pass case) |
| bad-duplicate-cols.csv | eval-001 (duplicate column names) |
| bad-special-chars.csv | eval-001 (special characters) |
| bad-mixed-types.csv | eval-001 (mixed types) |
| not-a-csv.txt | eval-001 (non-CSV file) |
| full-pipeline-test.csv | eval-002 (full pipeline — 2 datetime, 3 categorical, 5 numeric, 1 identifier, 1 text) |
| pii-dataset.csv | eval-003 (PII detection) |
| pii-transform-metadata.json | eval-003 Run A (Skill A PII flags carried forward) |
| all-identifiers.csv | eval-004 (fast-path no-opportunity) |
| ambiguous-data.csv | eval-004 (standard-path no-opportunity) |
| high-cardinality.csv | eval-005 (500 categories) |
| zero-variance.csv | eval-005 (constant column) |
| division-by-zero.csv | eval-005 (zero denominators) |
| column-explosion.csv | eval-005 (100+ category column) |
| bad-dates.csv | eval-005 (unparseable dates) |

All fixture data is synthetic and anonymized — no real PII.

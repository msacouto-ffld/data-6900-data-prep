---
name: data-profiling-and-cleaning
description: Use this skill when a user uploads a raw CSV and wants to understand, clean, or prepare it for analysis — including requests like "profile this dataset", "analyze the data quality", "clean this CSV", "fix the issues in this data", "run data profiling", or any similar natural-language request to inspect, diagnose, or repair tabular data. This skill always runs the full Skill A pipeline end-to-end. It first profiles the CSV (statistical summary, quality checks, PII scan, natural-language report) and then cleans it through a persona-validated 7-step transformation pipeline, producing the Skill A → Skill B handoff package (cleaned CSV, transformation report, transform metadata JSON, mistake log). Profiling and cleaning run as a single continuous pipeline — even requests framed as profiling-only continue through cleaning. Do NOT trigger for feature engineering (new columns, encodings, scaling) — that is Skill B.
---

# Data Profiling and Cleaning with Persona Validation (Skill A)

## Purpose

Skill A takes a raw CSV and produces a cleaned, decision-ready dataset plus the three-artifact handoff package that Skill B consumes. It runs as two connected features in a single session:

- **Feature 1 — Data Profiling**: ingest the CSV, run ydata-profiling, detect quality issues, scan for PII, generate charts, produce a 7-section natural language report verified by a Data Analyst persona.
- **Feature 2 — Data Cleaning**: feed Feature 1's structured output into a 7-step cleaning pipeline (column names → drop empty columns → type coercion → invalid categories → imputation → deduplication → outliers), validated by a multi-perspective review panel, executed deterministically, and packaged for Skill B.

Both features together deliver the Skill A guarantee: every decision is justified, every transformation passes through a persona loop, no raw data ever appears in logs or reports, and the cleaned CSV meets the Skill B handoff contract.

## Prerequisites

- A raw CSV uploaded to the Claude.ai session
- `pandas`, `numpy`, and `matplotlib` pre-installed in the Claude.ai sandbox; `ydata-profiling` ≥ 4.18.1 installed via pip at pipeline start; `scikit-learn` pre-installed (used by Feature 2)
- Dataset must fit within the hard limit of **500,000 cells** (rows × columns). Datasets between 100,000 and 500,000 cells trigger a warning but proceed.

No API keys, no configuration, no external services.

## Pipeline Overview

The full pipeline is 17 stages from upload to handoff. Stages 1–9 are Feature 1 (profiling); stages 10–17 are Feature 2 (cleaning). Read the relevant contract before running any stage — the contracts in `contracts/` are the source of truth.

### Feature 1 — Data Profiling

| # | Stage | Owner | Contract | Console prefix |
|---|-------|-------|----------|----------------|
| 1 | Install dependencies | Script | `contracts/install-dependencies.md` | 📦 |
| 2 | Validate input | Script | `contracts/validate-input.md` | 🔍 |
| 3 | Detect quality issues | Script | `contracts/detect-quality-issues.md` | 🔍 |
| 4 | Run ydata-profiling | Script | `contracts/run-profiling.md` | 📊 |
| 5 | Scan for PII | Script + LLM | `contracts/scan-pii.md` | 🔒 |
| 6 | Generate charts | Script | `contracts/generate-charts.md` | 📈 |
| 7 | Generate NL report | LLM | `contracts/generate-nl-report.md` | 📝 |
| 8 | Verify report (Data Analyst persona) | LLM | `contracts/verify-report.md` | 🔎 |
| 9 | Deliver profiling outputs | Script | `contracts/deliver-outputs.md` | 📥 |

### Feature 2 — Data Cleaning

| # | Stage | Owner | Reference | Console prefix |
|---|-------|-------|-----------|----------------|
| 10 | Load Feature 1 outputs | Script | `contracts/load-feature1-outputs.md` → `scripts/load_inputs.py` | 🔍 |
| 11 | Propose transformations (7 steps) | LLM | `PROMPTS.md` § Propose + `CATALOG.md` | 📋 |
| 12 | Review panel validates | LLM | `PROMPTS.md` § Review Panel | 🔎 |
| 13 | Execute approved transformations | Script | `contracts/execute-transformations.md` → `scripts/execute_transformations.py` | ⚙️ |
| 14 | Data Analyst verifies output | LLM | `PROMPTS.md` § Verify | 🔎 |
| 15 | Generate transformation report | LLM | `PROMPTS.md` § Report + `REPORT-TEMPLATE.md` | 📝 |
| 16 | Jargon scan | Script + LLM | `contracts/scan-jargon.md` → `scripts/jargon_scan.py` | 🔍 |
| 17 | Deliver cleaning outputs | Script | `contracts/deliver-outputs.md` → `scripts/deliver_outputs.py` | 📥 |

**No-issues fast-path**: if Feature 1's quality detections and PII scan all return `status: clean`, Feature 2 skips stages 11–16 and runs the light verification workflow (`PROMPTS.md` § Light Verification) to confirm the clean assessment. The original CSV is delivered as the "cleaned" output with a simplified report.

**Continuous pipeline**: profiling and cleaning always run as one pipeline. Even when the user frames the request as profiling-only ("give me a data quality report", "just profile this"), proceed through Feature 2 after Feature 1 delivers. The user can ignore the cleaning outputs if they only wanted the profile, but they always get both.

## Feature 1 Workflow

### 1. Install dependencies

Install `ydata-profiling` via `pip install ydata-profiling -q`. Verify import succeeds. If install fails, halt with the contract's error message. This must complete before anything else — ydata-profiling's install mutates pre-installed package versions, so it has to go first.

### 2. Validate input

Run the 8-check validation sequence in order: file exists → CSV extension → `pd.read_csv()` parses → ≥1 column → ≥1 row → cell count ≤ 500K (hard gate) → cell count 100K–500K (warning) → single-row (warning). Generate the profiling run ID in format `profile-YYYYMMDD-HHMMSS-XXXX`. Return `validation_result` matching DM-002.

Hard-gate failures halt the pipeline with actionable error messages from the contract.

### 3. Detect quality issues

Run four independent pandas-based checks (no ydata-profiling dependency):

- **Duplicate column names** — `df.columns.duplicated().any()`
- **Special characters in column names** — regex `r'^[a-zA-Z_][a-zA-Z0-9_]*$'` on each column name, flag non-matches
- **All-missing columns** — `df.isnull().all()`
- **Mixed types** — `df.apply(lambda col: col.dropna().map(type).nunique() > 1)` (note: `.map`, not the deprecated `.applymap`; drop NaN first to avoid counting `NoneType`)

Return `quality_detections` matching DM-003. Detections are informational — they do not halt the pipeline.

### 4. Run ydata-profiling

Build the config dict with **both** `sensitive=True` and `samples={"head": 0, "tail": 0}` as belt-and-suspenders privacy protection. Use `minimal=True` if cell count > 50,000. Run `ProfileReport(df, **config)`, export to `{run_id}-profile.html`, extract statistics via `report.get_description()` into DM-006.

On profiling failure, halt — downstream stages depend on the output.

### 5. Scan for PII (two layers)

**Layer 1 — Heuristic (script)**: normalize column names to lowercase, split on `_`, `-`, ` `, `.`, and match the resulting tokens against the 5 PII token lists from the contract (direct names, direct contact, direct identifiers, indirect, financial). Use **word-boundary matching**, not substring — `filename` must not match `name`. Layer 1 matches produce `confidence: "high"`, `detection_source: "column_name_pattern"`.

**Layer 2 — LLM value inspection**: for columns *not* flagged by Layer 1, extract the first 5 non-null values via `df[col].dropna().head(5).tolist()` and ask the LLM whether the values match PII patterns (email, phone, SSN, etc.). Layer 2 matches produce `confidence: "medium"`, `detection_source: "value_pattern_llm"`.

**This is the only place the LLM touches raw CSV values in Feature 1.** All other NL report content must come from profiling output and script detections. The NL report includes column names and PII categories only — **never** raw values.

Return results matching DM-004.

### 6. Generate charts

Use `matplotlib.use('Agg')` (non-interactive backend). Try `seaborn-v0_8-whitegrid` style with fallbacks. Figure DPI 150, 10pt body / 12pt titles.

| Chart | Filename | Inclusion rule |
|-------|----------|----------------|
| Missing values bar (horizontal, sorted descending, only >0%) | `{run_id}-chart-missing.png` | Omit if zero missing |
| Data type distribution bar | `{run_id}-chart-dtypes.png` | Always |
| Numeric histograms (grid, max 4 wide, bins=30) | `{run_id}-chart-histograms.png` | Omit if no numeric columns; cap at top 12 by variance, record the cap in `chart_metadata[].note` |

Chart failures are non-blocking — set `included: false` and continue. The NL report adapts its references based on `chart_metadata[].included`.

### 7. Generate the NL report

The LLM drafts a 7-section markdown report from profiling statistics, quality detections, PII scan results, and chart metadata. Sections: Dataset Overview → Key Findings → PII Scan Results → Column-Level Summary → Statistical Limitations → Recommendations → Verification Summary. See DM-008 for the full template.

**Plain-language constraints** (FR-007): basic statistical terms (mean, median, mode, outlier) are permitted without explanation; method-specific terms (z-score, IQR, kurtosis) must be explained on first use; all acronyms must be defined on first use; every metric must include context (% of rows, column name, before/after).

**No fabrication**: if the data is clean, the report says so. No unsupported claims.

**Column-Level Summary cap**: if the dataset has >30 columns, show the top 30 by issue severity (mixed types > all missing > special chars > duplicate names > high missing % > normal) and note the cap.

**Recommendation prioritization**: Critical (would cause Feature 2 to fail) → High (significantly affects data quality) → Medium (affects analysis quality) → Low (informational).

### 8. Verify the report (Data Analyst persona)

The LLM adopts the Data Analyst persona and applies the 7-item checklist to the draft: statistical accuracy, completeness, PII coverage, no fabrication, plain language, chart references, privacy. Appends the Verification Summary section with Corrections Made, Confirmed Accurate, and Review Status (PASS or CORRECTIONS APPLIED).

This is the "Test" step of the Verification Ritual (Read → Run → Test → Commit) for Feature 1.

### 9. Deliver profiling outputs

Write the final files:

- `{run_id}-profile.html` — ydata-profiling HTML (already written in stage 4)
- `{run_id}-summary.md` — final post-verification NL report
- `{run_id}-profiling-data.json` — DM-010 handoff (contains `validation_result`, `quality_detections`, `pii_scan`, `profiling_statistics`)
- `{run_id}-chart-*.png` — conditional charts

Display the NL report inline with charts embedded. Present all files for download using the contract's 📥 format. File write failures are non-blocking for inline delivery.

Once delivery is complete, **always continue to Feature 2**. Do not wait for a separate cleaning request.

## Feature 2 Workflow

Feature 2 always runs immediately after Feature 1 in the same session, so its inputs are guaranteed to be present in the sandbox.

### 10. Load Feature 1 outputs

Run `scripts/load_inputs.py`. This globs for `profile-*-profiling-data.json`, handles missing / multiple / ambiguous files, validates required top-level keys (`run_id`, `validation_result`, `quality_detections`, `pii_scan`, `profiling_statistics`), loads the NL report and original raw CSV, and generates the transform run ID in format `transform-YYYYMMDD-HHMMSS-XXXX`. Returns `run_metadata` (DM-102), `profiling_data`, `nl_report`, and `raw_df`.

### The 7 Cleaning Steps

Every proposal, review, and execution in stages 11–13 runs against this fixed order. Steps with no issues are explicitly marked as skipped — never silently omitted.

| Step | Issue type | Example strategies (see `CATALOG.md`) |
|------|-----------|---------------------------------------|
| 1 | Column name issues | `standardize_to_snake_case`, `remove_special_characters`, `rename_duplicates_with_suffix` |
| 2 | All-missing columns | `drop_column` |
| 3 | Type inconsistency | `coerce_to_target_type`, `parse_dates_infer_format`, `parse_currency_strip_symbols`, `parse_percent_to_float` |
| 4 | Invalid categories | `map_to_canonical_value`, `group_rare_into_other`, `flag_for_human_review` |
| 5 | Missing values | `drop_rows`, `drop_column`, `impute_mean`, `impute_median`, `impute_mode`, `impute_constant`, `impute_unknown`, `impute_most_frequent` |
| 6 | Duplicate rows | `drop_exact_keep_first`, `drop_exact_keep_last`, `keep_most_recent`, `keep_most_complete`, `flag_for_review` |
| 7 | Outliers | `cap_at_percentile`, `remove_rows`, `flag_only`, `winsorize` |

**Step dependency map** (from DM-106): Step 3 depends on 1; Step 4 depends on 3; Step 5 depends on 3; Step 6 depends on 5; Step 7 depends on 3 and 5. If the user skips a step with dependents, warn `⚠️ Skipping {step_name} may affect the accuracy of {dependent_step_name}. Proceeding with caution.`, log it, and include it in the transformation report.

### 11. Propose transformations

Read `PROMPTS.md` § Propose Transformations and `CATALOG.md`. Construct the proposal prompt with `profiling_data`, `nl_report`, and `run_metadata`. The LLM returns DM-104 — one entry per issue, mapped to a catalog strategy (or `is_custom: true` with extended justification if no catalog strategy fits). Custom strategies receive extra scrutiny in the review panel.

Validate with `scripts/schemas.py`. Print the console output showing all 7 steps with issues found or skipped.

**If `no_issues_detected` is true**, branch to the light verification workflow and jump to stage 17 with the original CSV as the "cleaned" output.

### 12. Run the review panel

Read `PROMPTS.md` § Review Panel. **Single LLM call** with a three-perspective system prompt:

- **Conservative View** — challenges statistical assumptions, distribution fit, potential bias, information loss
- **Business View** — evaluates real-world sensibility, domain context, stakeholder implications
- **Technical View** — checks mathematical soundness, threshold appropriateness, preservation of statistical properties

The panel returns DM-105 with a verdict and confidence score using deterministic fixed values:

| Condition | Score | Band |
|-----------|-------|------|
| Unanimous approval, catalog strategy | **95** | High |
| Unanimous approval, custom strategy | **82** | High |
| Majority approval with minor dissent | **67** | Medium |
| Significant dissent but consensus reached | **50** | Medium |
| No consensus (after 2 rejection loops) | **35** | Low |

**Rejection loop**: on any `verdict: REJECT`, send rejected transformations back to propose + review with the rejection reasoning as context. **Max 2 rejection loops per step.** After 2 loops still rejected → score = 35 → human review escalation (DM-113).

**Human review escalation** (confidence = 35): surface options to the user inline. User types a number → adopt that strategy. User types "skip" → record as skipped and check dependency warnings. User types guidance → re-run propose + review with guidance as context; if still no consensus, adopt the highest-scoring option with the note "Adopted based on user guidance; review panel dissent noted." Record decisions in DM-106 `human_review_decisions` and the mistake log.

Console output is condensed: all-approved steps show as a single summary line; only medium/low confidence or rejected steps get expanded detail.

### 13. Execute approved transformations

Run `scripts/execute_transformations.py` with `raw_df`, the approved plan (DM-106), and `run_metadata`. The orchestrator dispatches to the seven step functions in order:

- `step_1_column_names.py` — column names only, never data values
- `step_2_drop_missing.py` — validates 100% missing **before** dropping; raises if not
- `step_3_type_coercion.py` — dispatches on strategy (`coerce_to_target_type`, `parse_dates_infer_format` with `format='mixed'`, `parse_currency_strip_symbols`, `parse_percent_to_float`)
- `step_4_invalid_categories.py`
- `step_5_imputation.py` — scikit-learn `SimpleImputer` with `random_state=42` where applicable
- `step_6_deduplication.py`
- `step_7_outliers.py`

Each step captures `metrics_before` and `metrics_after` via `scripts/metrics.py` (dataset-level for all steps; column-level only for affected and flagged columns). `scripts/high_impact.py` checks against DM-108 thresholds and records flags in DM-107.

**Never execute LLM-generated code.** Every transformation is dispatched to a pre-built code path by strategy name. Custom strategies that survived the review panel are documented but still dispatched to pre-built paths.

Write the cleaned CSV to `{transform_run_id}-cleaned.csv`.

### 14. Verify the output (Data Analyst persona)

Read `PROMPTS.md` § Verify. The Data Analyst persona compares before / after using the step results and checks for unintended side effects — unexpected row loss, distribution shifts, unapproved changes, unexpectedly empty columns, metric consistency. Confirms PASS, records CORRECTIONS APPLIED, or flags ISSUES FOUND.

This is the "Test" step of the Verification Ritual for Feature 2. It happens **before** report generation — the Verification Summary section is populated from the result.

### 15. Generate the transformation report

Read `PROMPTS.md` § Report Generation and `REPORT-TEMPLATE.md` (DM-109 template). Construct the prompt with `step_results`, `approved_plan`, `review_outputs`, `verification_result`, `run_metadata`, `profiling_data`, and `high_impact_flags`.

Every transformation gets the mandatory 3-part justification — **What was done? → Why? → What is the impact?** — plus before/after comparisons for row count, column count, missing values, and at least one aggregate metric per affected column. Plus the confidence score. Plus any rejected transformations with their reasons.

**High-impact flags** (from DM-108 thresholds) must be surfaced with both the actual value and the threshold that triggered them — never silently applied.

### 16. Jargon scan

Run `scripts/jargon_scan.py` — Layer 1 finds uppercase token sequences via `\b[A-Z]{2,}\b`, removes whitelisted acronyms (CSV, HTML, JSON, NaN, PII, ID, LLM, NL, ASCII, UTC, ISO, PDF, API), and checks the remainder for first-use definitions. Returns the list of truly undefined terms.

If any undefined terms are found, make **one** targeted LLM call to define or replace them and apply corrections in place. Do not re-scan. Log the fix as a `jargon_scan_violation` event in the mistake log.

### 17. Deliver cleaning outputs

Run `scripts/deliver_outputs.py`. This:

- Writes `{transform_run_id}-transform-report.md` (final post-jargon-scan report)
- Writes `{transform_run_id}-transform-metadata.json` (DM-110 — the Skill B handoff artifact). Populate from `run_metadata`, `approved_plan`, `profiling_data` PII warnings, and skipped transformations from **both** sources: `user_skipped` (from human review) and `skill_boundary` (deferred to Skill B, e.g., normalization). Each entry carries a `source` field.
- Writes the mistake log to `{transform_run_id}-mistake-log.json` via `write_mistake_log()` — **inside a try/finally**, so it persists even on pipeline error
- Verifies `{transform_run_id}-cleaned.csv` exists (already written in stage 13)
- Displays the report inline and presents four downloads in the contract's 📥 format:

```
📥 Your cleaning outputs are ready for download:
   • {run_id}-cleaned.csv — Cleaned dataset ({rows} rows × {cols} columns)
   • {run_id}-transform-report.md — Transformation report
   • {run_id}-transform-metadata.json — Transformation metadata
     (for feature engineering and downstream processing)

A pipeline log ({run_id}-mistake-log.json) is also available
if you need audit details.
```

End with the "What to Do Next" guidance from quickstart Step 9, pointing the user to Skill B (feature engineering) as the natural next step. File write failures are non-blocking for inline delivery.

## Guardrails

- **Never execute LLM-generated code.** The orchestrator dispatches to pre-built code paths by strategy name only.
- **Never apply a transformation that wasn't approved through the review panel.** FR-107 is non-negotiable. No transformation passes unchallenged (SC-102).
- **Never include raw data values in the NL report, transformation report, mistake log, or any exported log.** Column names and aggregate descriptions only. `affected_columns` holds names, never values. The only exception is PII Layer 2 inspection — and even then, raw values are never persisted or displayed, only shown to the LLM in memory for pattern classification.
- **Never silently apply a high-impact transformation.** DM-108 thresholds must be surfaced in the report with both the actual value and the threshold that triggered them.
- **Never attempt feature engineering.** Normalization, encoding, scaling, and derived columns are recorded as `skill_boundary` skipped transformations and handed off to Skill B via the metadata JSON.
- **Never fabricate issues.** If profiling finds nothing, the NL report says so. If cleaning finds nothing, the fast-path runs and the CSV is returned unchanged.
- **Install ydata-profiling before anything else.** It mutates pre-installed package versions, so any other work done first risks being invalidated.
- **Determinism where possible**: `random_state=42` on scikit-learn imputers; fixed catalog strategies; deterministic confidence score assignment; `matplotlib.use('Agg')`; ydata-profiling config with both `sensitive=True` and `samples={"head": 0, "tail": 0}`. Identical inputs produce identical outputs (SC-109).

## Mistake Log (DM-112)

Every Feature 2 stage writes to the mistake log via `scripts/mistake_log.py`. Event types from DM-112: `persona_rejection`, `execution_error`, `edge_case_warning`, `consensus_failure`, `high_impact_flag`, `human_review_decision`. Step 0 (pipeline-level) events include Feature 1 output validation failure, no-issues path triggered, pipeline initialization error, report generation failure, and jargon scan violation.

The log is written via try/finally in `deliver_outputs.py` so it persists even on pipeline error, and is always presented alongside the three primary outputs.

Privacy: `affected_columns` holds column names only. `description` and `resolution` use generic descriptions, never data samples.

## Error Reference

| Error | Cause | What to do |
|-------|-------|------------|
| ydata-profiling install failed | pip install error | Start a new session and retry |
| File not found / not a valid CSV | Upload problem or file format | Re-upload a valid CSV |
| Empty CSV (headers only, no rows) | No data to profile | Upload a CSV with at least one row |
| Dataset exceeds profiling limit (>500K cells) | File too large | Sample or split the dataset and re-upload |
| Profiling failed | ydata-profiling exception | Start a new session; try uploading a smaller sample |
| No profiling data found (Feature 2 stage) | Feature 1 outputs missing from sandbox | Run profiling first: upload CSV and request profiling |
| Profiling data incomplete or corrupted | JSON missing required keys | Re-run profiling in a new session |
| Multiple profiling runs found | Ambiguous which to use | Ask the user which profiling run to load |
| Transformation failed at step {n} | Python error during execution | Start a new session, re-upload the CSV, re-run the full pipeline. Session outputs cannot be reused across sessions — downloading as a backup is recommended. |
| Verification found a discrepancy | Output doesn't match expected state | Review the report; consider re-running |
| Pipeline crashed mid-execution | Session state lost | Start a new session and re-upload |
| Review panel could not reach consensus | Personas disagreed (score = 35) | User chooses an option, skips, or provides guidance per the escalation flow |
| Skipped step has a dependent | Dependency chain broken | Warning issued, pipeline continues with caution flag in report |
| High-impact flag triggered | Transformation exceeded DM-108 threshold | Flagged in report with actual value vs. threshold; user should review before handing off to Skill B |
| Output file write failed | Sandbox write error | Report delivered inline; user copies manually |

## Reference Files

- `contracts/` — all pipeline step contracts for both features (install-dependencies, validate-input, detect-quality-issues, scan-pii, run-profiling, generate-charts, generate-nl-report, verify-report, deliver-outputs for Feature 1; load-feature1-outputs, execute-transformations, scan-jargon, deliver-outputs, collect-mistake-log for Feature 2; plus evaluation-suite)
- `PROMPTS.md` — full LLM persona prompts (NL report generation, Data Analyst verification for Feature 1; Propose Transformations, Review Panel, Verify, Report Generation, Light Verification for Feature 2)
- `CATALOG.md` — DM-103 transformation catalog with all strategies and required parameters
- `REPORT-TEMPLATE.md` — DM-109 transformation report template
- `scripts/` — pipeline entry points and utilities: `load_inputs.py`, `execute_transformations.py`, `jargon_scan.py`, `deliver_outputs.py`, `step_1_column_names.py` through `step_7_outliers.py`, plus shared utilities (`schemas.py`, `catalog.py`, `thresholds.py`, `metrics.py`, `high_impact.py`, `run_id.py`, `mistake_log.py`)
- `data-model.md` — all schemas (Feature 1: DM-001 to DM-010; Feature 2: DM-101 to DM-113)
- `quickstart.md` — end-to-end walkthroughs with exact console output and user-facing messages

Read the relevant contract or prompt section before running any stage. The contracts are the source of truth — this SKILL.md is the map, not the territory.

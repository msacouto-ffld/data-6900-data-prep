---
name: feature-engineering

description: Use this skill when a user wants to engineer features from a cleaned CSV produced by Skill A (Data Cleaning). Triggers on natural-language requests like "engineer features for this dataset", "what features can you create from this data", "run feature engineering on the uploaded CSV", or any similar request to derive new columns, encode categoricals, extract datetime parts, aggregate group-level metrics, or normalize/scale numeric columns. Requires a cleaned CSV that conforms to the Skill A handoff contract; ideally also accepts Skill A's transform-report.md and transform-metadata.json as part of the three-artifact handoff. Do NOT trigger for raw uncleaned CSVs — redirect the user to Skill A first. Do NOT trigger for model training, feature selection, or statistical analysis tasks — this skill only creates features, it does not evaluate them.
---

# Feature Engineering with Persona Validation (Skill B)

## Purpose

Skill B takes a cleaned CSV from Skill A and produces a feature-engineered CSV ready for analysis or modeling. It runs an 11-step pipeline that validates the handoff, proposes features in 6 batches (datetime → text → aggregations → derived → encoding → normalization), challenges every proposal through 3 LLM personas, executes approved features via pandas/numpy/scikit-learn, verifies the output through a 4th persona, and delivers a feature-engineered CSV, transformation report, data dictionary, and mistake log.

Every decision is justified and every engineered column is prefixed `feat_` so downstream users can tell original columns from generated ones.

## Prerequisites

- A cleaned CSV that conforms to the Skill A handoff contract (snake_case ASCII column names, no duplicates, no all-missing columns, consistent types within each column, missing values resolved or justified)
- Preferably the full three-artifact handoff from Skill A: cleaned CSV + `transform-report.md` + `transform-metadata.json`. If only the CSV is present, Skill B falls back to CSV-only mode and runs its own PII heuristic
- `pandas`, `numpy`, and `scikit-learn` available in the Claude.ai sandbox (verify via `scripts/check_deps.py` before any pipeline code runs — see T001)

If the user uploads a raw CSV or a file that fails the handoff contract, **stop immediately** and redirect them to Skill A. Do not attempt to fix Skill A's output.

## Pipeline Overview

The pipeline has 11 steps in fixed order. Each step has a contract in `contracts/` defining its exact inputs, outputs, console output, and error conditions. Read the contract for any step you are about to run — do not improvise.

| # | Step | Owner | Contract | Console prefix |
|---|------|-------|----------|----------------|
| 1 | Validate handoff | Script | `contracts/validate-handoff.md` | 🔍 |
| 2 | Scan PII | Script | `contracts/scan-pii.md` | 🔒 |
| 3 | Generate dataset summary | Script | `contracts/generate-dataset-summary.md` | 📋 |
| 4 | Propose features (×6 batches) | LLM | `contracts/propose-features.md` | 📋 |
| 5 | Challenge features (×6 batches) | LLM | `contracts/challenge-features.md` | 🔎 |
| 6 | Execute transformations | Script | `contracts/execute-transformations.md` | ⚙️ |
| 7 | Verify output | LLM | `contracts/verify-output.md` | 🔎 |
| 8 | Scan jargon | Script + LLM | `contracts/scan-jargon.md` | 🔍 |
| 9 | Generate report | LLM | `contracts/generate-report.md` | 📝 |
| 10 | Generate dictionary | LLM | `contracts/generate-dictionary.md` | 📝 |
| 11 | Deliver outputs | Script | `contracts/deliver-outputs.md` | 📥 |

The no-opportunity **fast-path** short-circuits steps 4–7 when the dataset has ≤2 columns or every column is a unique identifier. In that case, produce a no-opportunity report and return the input CSV unchanged.

## Workflow

Follow these steps in order. Each step has a referenced contract — read it before executing.

### 1. Validate the handoff

Run `scripts/validate_handoff.py` against the uploaded file(s). This:

- Generates the run ID in format `feature-YYYYMMDD-HHMMSS-XXXX` (see `scripts/run_id.py`)
- Checks file is a valid CSV, has ≥1 column and ≥1 row, and ≤500,000 cells (warn at 100k–500k, reject above 500k)
- If `transform-metadata.json` is present, verifies `produced_by == "skill_a"` and contract version `1.0`
- Verifies column names are snake_case ASCII, no duplicates, no all-missing columns, no exact duplicate rows, consistent types per column
- Returns a `validation_result` dict per schema DM-003

**If any hard gate fails, stop the pipeline.** Display the contract's actionable error message, log the violation via `log_event`, and do not proceed. See `contracts/validate-handoff.md` for the full list of checks and error messages.

### 2. Scan for PII

Run `scripts/scan_pii.py`. Two modes:

- **Metadata mode** (Skill A metadata JSON present): read `pii_warnings` directly from the metadata; console shows `loaded N flags from Skill A transform metadata`
- **Heuristic mode** (CSV only): normalize column names, split on delimiters, match against the PII token lists in `contracts/scan-pii.md` (5 categories: names, contact info, identifiers, financial, geographic)

PII findings are **warnings only** in V1 — they do not halt the pipeline. But they must be logged via `log_event`, surfaced in the transformation report, and the Domain Expert persona must challenge any feature derived from a PII-flagged column. Sample values from PII columns must be replaced with `["[PII — values hidden]"]` in the dataset summary.

### 3. Generate the dataset summary

Run `scripts/generate_dataset_summary.py`. Computes per-column dtype, missing count/percentage, unique count, `is_unique` flag, plus numeric stats (mean, std, min, max, median) for numeric columns, and up to 5 sample values per column (hidden for PII columns). Attach Skill A's transform report text as `skill_a_context` and metadata JSON as `skill_a_metadata` if available. Returns `dataset_summary` matching DM-004.

### 4. Check the fast-path

Before entering the batch loop, check if the dataset has ≤2 columns OR every column is a unique identifier. If so:

- Skip steps 4–7 entirely
- Generate a no-opportunity report stating the specific reason
- Return the input CSV unchanged as the output
- Jump to step 11 (deliver outputs)

### 5. Propose + Challenge — 6 batches

For each batch type in fixed order, run the propose → challenge loop. The transformation order is locked (create new information first, transform representations last):

1. **datetime_extraction** — day of week, hour, month, etc. from datetime columns
2. **text_features** — string length, word count, regex patterns (basic only, no NLP)
3. **aggregations** — `groupby().transform()` for group-level KPIs mapped to row level. **Cap: 10 proposals per batch.** Extras go to the report's deferred section.
4. **derived_columns** — ratios and composite columns
5. **categorical_encoding** — one-hot, label encoding
6. **normalization_scaling** — standardization, min-max, etc.

For each active batch:

1. Call `propose_features` with `batch_type`, `dataset_summary`, and `approved_features_so_far`. The LLM returns a `feature_proposal_batch` matching DM-005. See `contracts/propose-features.md` for the 7 prompt constraints.
2. Call `challenge_features` three times — once per persona:
   - **Feature Relevance Skeptic** — questions whether the feature adds analytical value
   - **Statistical Reviewer** — questions distribution, cardinality, collinearity
   - **Domain Expert** — questions real-world meaning and PII exposure
3. Each persona returns APPROVE / REJECT / MODIFY with reasoning (schema DM-006).
4. On rejection, LLM proposes an alternative and personas review again. **Max 2 rejection cycles per feature. Max 5 total rejected features per batch** — remaining rejections drop the feature without retry.
5. Approved features for this batch are appended to `approved_features_so_far`, each with a deterministic confidence score: **95** (strong consensus), **82** (minor note), **67** (caveats), **50** (unresolved), **35** (contested).
6. Out-of-type proposals (e.g., the datetime batch proposes a ratio) are queued for the correct batch, not dropped.

**Empty batches** (e.g., no datetime columns): the LLM explicitly notes the batch was skipped and why. Record in the report.

See `contracts/propose-features.md` and `contracts/challenge-features.md` for the full persona system prompts and output schemas.

### 6. Execute approved transformations

Run `scripts/execute_transformations.py`. Applies approved features in batch order (datetime → text → aggregations → derived → encoding → normalization), alphabetical within each batch. Every engineered column is prefixed `feat_`. Original cleaned columns are preserved unless an approved decision explicitly removes one (e.g., dropping the original categorical after one-hot encoding).

**Never execute LLM-generated code directly.** The script uses pre-built code paths; the LLM's `implementation_hint` field is advisory only. See `contracts/execute-transformations.md`.

Log execution errors via `log_event` as `execution_error` events.

### 7. Verify the output (Data Analyst persona)

Call `verify_output` — the 4th persona (Data Analyst) reviews the before/after state. This is the "Test" step of the Verification Ritual (Read → Run → Test → Commit). Runs 9 checks including row count preservation, column count delta, dtype consistency, NaN/infinity presence, and any unapproved changes.

If uncorrectable issues are found, halt and flag for human review. Otherwise, return `verification_result` matching DM-008. See `contracts/verify-output.md`.

### 8. Scan for jargon

Run `scripts/scan_jargon.py` (Layer 1: ~20-term script scan) and then the verification persona (Layer 2). Catches technical terms that would break plain-language compliance in the report. See `contracts/scan-jargon.md`.

### 9. Generate the transformation report

Call `generate_report`. Follows the DM-010 template with the mandatory 3-part justification per feature: **What was done? → Why? → What is the impact?** Plus a benchmark comparison (what the feature enables, what you'd lose without it). Includes:

- Pipeline summary (features proposed, approved, rejected, batches skipped)
- PII scan results with source
- One section per batch (with "Skipped — no X columns" for empty batches)
- Before/after shape and distributions
- Confidence score per feature
- Rejected transformations with reasons
- Deferred aggregates list (if Batch 3 hit the cap)
- Verification Summary from step 7
- Flags for high-cardinality encoding, zero-variance columns, NaN/infinity producers

See `contracts/generate-report.md` and DM-010.

### 10. Generate the data dictionary

Call `generate_dictionary`. Produces a plain-language entry for every column in the output CSV — originals and engineered — per DM-011. Engineered entries link back to the report section that justifies them. See `contracts/generate-dictionary.md`.

### 11. Deliver outputs

Run `scripts/deliver_outputs.py`. Writes all files to the sandbox with the `{run_id}-` prefix:

- `{run_id}-features.csv` — the feature-engineered CSV
- `{run_id}-transformation-report.md` — the report (displayed inline, truncated if >10 features)
- `{run_id}-data-dictionary.md` — the data dictionary (displayed inline after the report)
- `{run_id}-mistake-log.md` — the append-as-you-go operational record (**always presented** alongside the three primary files, regardless of whether anything went wrong)

Present downloads using the 📥 format from `contracts/deliver-outputs.md`. File write failures are non-blocking for inline delivery. End with the "What to Do Next" guidance.

## Guardrails

- **Never apply a transformation that wasn't approved through the persona loop.** FR-209 is non-negotiable.
- **Never execute LLM-generated code.** The LLM's implementation hints are advisory; executed code comes from pre-built paths in `scripts/execute_transformations.py`.
- **Never include raw data values in the mistake log or any output log.** Column names and aggregate descriptions only. Privacy guardrail — see DM-012.
- **Never drop original cleaned columns** unless an approved decision explicitly removes one.
- **Never proceed past a handoff contract violation.** Stop, log, surface the actionable error, and wait for human action.
- **Never fabricate a PII clearance.** If metadata is absent, the heuristic runs; findings (or lack of findings) are reported honestly with the source noted.
- Every engineered column name starts with `feat_`. No exceptions.

## Mistake Log

Every pipeline step calls `log_event` (see `scripts/mistake_log.py`) for the relevant event types from DM-012: `handoff_contract_violation`, `handoff_contract_warning`, `pii_warning`, `persona_rejection`, `persona_modification`, `edge_case_triggered`, `execution_error`, `verification_correction`, `verification_issue`, `jargon_scan_flag`. Writes are wrapped in try/finally so log failures never crash the pipeline. The mistake log is always delivered to the user in step 11.

## Error Reference

| Error | Cause | What to do |
|-------|-------|------------|
| Handoff contract violation: column names not snake_case | Skill A didn't standardize, or user uploaded a non-Skill-A CSV | Re-run Skill A, or rename columns manually and re-upload |
| Handoff contract violation: CSV not produced by Skill A | `transform-metadata.json` has wrong `produced_by` field | Run Skill A on the raw data first |
| Dataset exceeds feature engineering limit (>500,000 cells) | File too large for V1 | Sample or split the dataset and re-upload |
| Dependency error: required library not available | `pandas`, `numpy`, or `scikit-learn` missing from sandbox | Start a new Claude.ai session |
| Persona loop could not reach consensus after 2 cycles | 3 personas disagreed beyond rejection cap | Feature is dropped with documented reason; pipeline continues |
| Verification found uncorrectable issue | Data Analyst persona flagged a problem the script can't fix | Halt and surface the issue for human review |
| Batch 3 hit aggregate cap | >10 aggregate proposals | Top 10 proposed, rest documented as deferred in the report |
| Fast-path triggered: no feature engineering opportunities | ≤2 columns or all identifiers | Output CSV = input CSV; report explains the reason |
| Execution error at batch {n} | pandas/numpy error during execution | Logged as `execution_error`; failing feature is dropped, pipeline continues with remaining features |

## Reference Files

- `contracts/` — all 11 step contracts (validate-handoff, scan-pii, generate-dataset-summary, propose-features, challenge-features, execute-transformations, verify-output, scan-jargon, generate-report, generate-dictionary, deliver-outputs) plus the evaluation suite
- `data-model.md` — all 12 schemas (DM-001 through DM-012)
- `PROMPTS.md` — full LLM prompt templates for the 4 personas (Feature Relevance Skeptic, Statistical Reviewer, Domain Expert, Data Analyst), the 6 feature proposal prompts, and the report/dictionary generation prompts
- `quickstart.md` — end-to-end walkthrough with exact console output and user-facing messages
- `scripts/` — `validate_handoff.py`, `scan_pii.py`, `generate_dataset_summary.py`, `execute_transformations.py`, `scan_jargon.py`, `deliver_outputs.py`, `run_id.py`, `mistake_log.py`, `check_deps.py`

Read the contract for any step before executing it. The contracts are the source of truth — this SKILL.md is a map, not a replacement.
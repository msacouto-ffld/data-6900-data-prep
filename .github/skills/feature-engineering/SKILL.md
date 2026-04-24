---
name: feature-engineering
description: Use this skill when a user uploads a cleaned CSV (from Skill A or any clean tabular dataset) and wants to create new features for analysis or modeling — including requests like "engineer features for this dataset", "what features can you create from this data", "run feature engineering", "create derived columns", "encode categorical variables", or any similar request to derive, encode, scale, or aggregate columns. This skill validates the input against the Skill A handoff contract, scans for PII, proposes features in 6 batches with 3-persona validation, executes approved transformations, and delivers a feature-engineered CSV plus transformation report and data dictionary. Do NOT trigger for data profiling or cleaning — that is Skill A.
---

# Feature Engineering with Persona Validation (Skill B)

## Purpose

Takes a cleaned CSV (ideally from Skill A) and engineers new features: date/time extraction, text features, aggregate metrics, derived ratios, categorical encoding, and normalization. Every proposed feature is challenged by three personas before execution. Produces a feature-engineered CSV, transformation report, data dictionary, and mistake log.

## Prerequisites

- Cleaned CSV uploaded to the session
- Optionally: Skill A's `transform-metadata.json` and `transform-report.md` (provides PII flags and cleaning context)
- Hard limit: 500,000 cells. Warning at 100,000+.

## Workflow

Copy this checklist and track progress:

```
Pipeline Progress:
- [ ] Validate handoff contract
- [ ] Scan for PII
- [ ] Generate dataset summary
- [ ] Check fast-path (no opportunities?)
- [ ] Batch 1: Date/Time Extraction — propose + challenge
- [ ] Batch 2: Text Features — propose + challenge
- [ ] Batch 3: Aggregate Features — propose + challenge
- [ ] Batch 4: Derived Columns — propose + challenge
- [ ] Batch 5: Categorical Encoding — propose + challenge
- [ ] Batch 6: Normalization / Scaling — propose + challenge
- [ ] Execute all approved transformations
- [ ] Data Analyst verification
- [ ] Evaluate feature value (model comparison)
- [ ] Generate report + dictionary
- [ ] Jargon scan
- [ ] Deliver outputs
```

### Stage 1: Validate handoff

Run `scripts/validate_handoff.py`. Applies 16 checks from DM-001:

- File parses, has columns and rows, within cell limit
- If metadata JSON present: check `produced_by == "skill_a"` and `handoff_contract_version == "1.0"`
- No duplicate column names, all snake_case ASCII, no all-missing columns, no exact duplicate rows, consistent types per column

Hard-gate failures halt with actionable messages pointing back to Skill A. If metadata is absent, fall back to CSV-only mode (skip provenance checks, run own PII scan).

Generates run ID: `feature-YYYYMMDD-HHMMSS-XXXX`.

### Stage 2: Scan for PII

Run `scripts/scan_pii.py`. Two paths:

1. **Metadata present**: read `pii_warnings` from Skill A's `transform-metadata.json`
2. **No metadata**: run heuristic column-name scan (same token lists as Skill A)

PII-flagged columns get `sample_values: ["[PII — values hidden]"]` in the dataset summary. The LLM notes PII columns when proposing features, and the Domain Expert persona challenges features derived from PII columns. PII does not halt the pipeline — warnings only.

### Stage 3: Generate dataset summary

Run `scripts/generate_dataset_summary.py`. Builds DM-004: per-column dtype, missing count, unique count, sample values (PII-masked), numeric stats. Attaches Skill A metadata and report as context for the LLM. The LLM never sees the raw CSV — only this summary.

### Stage 4: Propose + challenge (6 batches)

**Fast-path check**: if all columns are unique identifiers or the dataset has ≤2 columns, skip to delivery with the original CSV unchanged and a "no opportunities" report.

Otherwise, loop through 6 batches in order:

| Batch | Type | Methods |
|-------|------|---------|
| 1 | Date/Time Extraction | `extract_day_of_week`, `extract_hour`, `extract_month`, `extract_quarter` |
| 2 | Text Features | `text_string_length`, `text_word_count` |
| 3 | Aggregate Features | `groupby_agg` (max 10 per batch) |
| 4 | Derived Columns | `derived_ratio`, `derived_difference` |
| 5 | Categorical Encoding | `one_hot_encode`, `label_encode` |
| 6 | Normalization / Scaling | `min_max_scale`, `z_score_scale` |

For each batch:

1. **Propose** — LLM call using [PROMPTS.md](PROMPTS.md) § Propose Features. Pass dataset summary, batch type, and already-approved features. Output: DM-005 JSON. If no columns of this type exist, skip with `skipped_reason`.

2. **Challenge** — Three separate LLM calls, one per persona:
   - **Feature Relevance Skeptic** ([PROMPTS.md](PROMPTS.md) § Feature Relevance Skeptic) — catches redundancy
   - **Statistical Reviewer** ([PROMPTS.md](PROMPTS.md) § Statistical Reviewer) — catches invalid methods
   - **Domain Expert** ([PROMPTS.md](PROMPTS.md) § Domain Expert) — catches business-nonsense

   Each returns DM-006 JSON. The pipeline script counts challenges and assigns confidence scores deterministically:

   | Condition | Score | Band |
   |-----------|-------|------|
   | 0 challenges across all 3 personas | 95 | High |
   | Challenges raised, all resolved, no caveats | 82 | High |
   | Challenges raised, all resolved, with caveats | 67 | Medium |
   | Challenges raised, not all resolved | 50 | Medium |
   | Original rejected, alternative adopted | 35 | Low |

3. **Rejection loop** — if any persona rejects: re-propose alternative (max 2 cycles per feature, max 5 rejected per batch before remaining are dropped). Log rejections in mistake log.

4. **Update tracker** — add approved features to the running DM-007 list so subsequent batches can reference them.

### Stage 5: Execute transformations

Run `scripts/execute_features.py`. Applies all approved features in batch order (1→6), alphabetical within each batch. Every new column gets the `feat_` prefix (added by the script, never by the LLM).

Pre-built implementations — the LLM's `implementation_hint` is advisory only:

| Method | Implementation |
|--------|---------------|
| `extract_day_of_week` | `pd.to_datetime(df[col]).dt.dayofweek` |
| `extract_hour/month/quarter` | Same pattern with `.dt.hour/month/quarter` |
| `text_string_length` | `df[col].astype(str).str.len()` |
| `text_word_count` | `df[col].astype(str).str.split().str.len()` |
| `groupby_agg` | `df.groupby(key)[col].agg(func)` + merge back |
| `derived_ratio` | `df[col_a] / df[col_b]`, division-by-zero → NaN |
| `derived_difference` | `df[col_a] - df[col_b]` |
| `one_hot_encode` | `pd.get_dummies()` with snake_case column names |
| `label_encode` | `sklearn.preprocessing.LabelEncoder` |
| `min_max_scale` | `sklearn.preprocessing.MinMaxScaler` |
| `z_score_scale` | `sklearn.preprocessing.StandardScaler` |

Edge cases handled: division by zero → NaN, infinity → NaN, zero-variance → skip scaling, NaN from bad date parsing → logged. Original columns preserved. Row count preserved.

Writes `{run_id}-engineered.csv`.

### Stage 6: Verify output

LLM call using [PROMPTS.md](PROMPTS.md) § Verify Output. Data Analyst applies 9-item checklist: row count preserved, original columns intact, feat_ prefix, expected columns present, no unexpected NaN, no infinity, encoding correct, scaling correct, no data leakage. Returns DM-008 JSON.

### Stage 7: Evaluate feature value

Run `scripts/evaluate_features.py`. Trains a simple model (RandomForest) on the original features only (baseline), then on original + engineered features, and compares performance using 5-fold cross-validation. This is the external quality control that proves the engineered features actually add value — the personas validate the process, but only a model comparison validates the outcome.

The script auto-detects the target column (looks for common names like `target`, `label`, `class`, or the last categorical column with 2–20 unique values). If no target is found, the comparison is skipped with a note.

Output is a comparison table included in the transformation report:

```
📊 Evaluating feature value...
   Target column: nobeyesdad
   Task type: classification
   Model: RandomForest (n_estimators=100, max_depth=30)

   BASELINE (16 original features)
     Accuracy: 0.6809 (±0.0329)
     F1 Weighted: 0.6319 (±0.0238)

   WITH ENGINEERED FEATURES (35 total features)
     Accuracy: 0.8241 (±0.0394)
     F1 Weighted: 0.8080 (±0.0436)

   DELTA
     Accuracy: +0.1432
     F1 Weighted: +0.1761

   ✅ Engineered features improved accuracy by 0.1432
```

If no target is detected, comparison is skipped gracefully — it does not halt the pipeline.

### Stage 8: Generate report + dictionary

Two parallel LLM calls:

- **Report** — [PROMPTS.md](PROMPTS.md) § Generate Report. Every feature gets 3-part template (What/Why/Impact) + benchmark + confidence score. If >10 features, inline version shows summary table + top 5 detailed, full report in download.

- **Dictionary** — [PROMPTS.md](PROMPTS.md) § Generate Dictionary. Each entry is self-contained: a data scientist can understand it without referring to the report. Required fields: name, description, dtype, source columns, method, value range, missing values, notes.

Then run `scripts/scan_jargon.py` on both. Checks ~24 method-specific terms (one-hot encoding, z-score, normalization, etc.) for first-use explanations. If violations found, one LLM call to add definitions.

### Stage 9: Deliver outputs

Run `scripts/deliver_outputs.py`. Displays report and dictionary inline. Presents downloads:

```
📥 Your feature engineering outputs are ready:
   • {run_id}-engineered.csv
     — Feature-engineered dataset ({original} original + {new} new columns)
   • {run_id}-transformation-report.md
   • {run_id}-data-dictionary.md

Engineered columns are prefixed with 'feat_' — use
df.filter(like='feat_') to select them.

📋 Mistake log: {run_id}-mistake-log.md
```

## Guardrails

- **Never execute LLM-generated code.** `implementation_hint` is advisory. All transformations use pre-built code paths.
- **Never apply features that weren't approved through the persona loop.**
- **Never include raw data values** in reports, dictionary, or logs. Column names and aggregates only.
- **`feat_` prefix** is added by the script, never by the LLM. Enforced in execution.
- **Original columns preserved.** Row count preserved. Row order preserved.
- **PII-flagged columns** get masked sample values and explicit LLM warnings.

## Error Reference

| Error | What to do |
|-------|------------|
| Handoff contract violation (duplicates, special chars, mixed types) | Re-run Skill A or fix manually |
| Not a valid CSV / empty CSV | Re-upload a valid CSV |
| Exceeds 500K cells | Reduce rows or columns |
| Execution error (division by zero, encoding failure) | Auto-handled: NaN replacement, logged, pipeline continues |
| No feature engineering opportunities | Original CSV returned unchanged with report |
| Pipeline crash | New session, re-upload CSV |

## Reference Files

- [PROMPTS.md](PROMPTS.md) — all LLM prompt templates (8 sections: propose, 3 personas, verify, evaluate narrative, report, dictionary)
- `scripts/` — all pipeline scripts and utilities (including evaluate_features.py)

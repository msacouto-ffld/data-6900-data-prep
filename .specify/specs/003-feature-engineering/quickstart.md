# Feature Engineering with Persona Validation — Phase 1 Quickstart

**Date**: 2026-04-06 | **Spec**: Feature 003 — Feature Engineering | **Status**: Draft

## Purpose

Minimal end-to-end walkthrough of Skill B: user uploads a cleaned CSV from Skill A, Skill B engineers features, and the user downloads the results. Shows exactly what the user does and what the system returns at each step.

## Prerequisites

- A Claude.ai account with access to the conversation interface
- A cleaned CSV produced by Skill A (or any CSV that meets the handoff contract)
- **Expected from Skill A:** Skill A produces three artifacts together (cleaned CSV, transform report, transform metadata JSON). Upload all three when available — they give Skill B everything it needs. If you only have the CSV, Skill B falls back to a reduced mode.

No special setup required — no API keys, no local installation, no configuration.

---

## Step 1 — Upload Files and Request Feature Engineering

Upload your cleaned CSV using the file attachment button in Claude.ai. If you have Skill A's transform report and transform metadata JSON, upload those too — they're part of the standard three-artifact handoff.

Then ask for feature engineering in natural language. Examples:

```
Engineer features for this dataset.
What features can you create from this data?
Run feature engineering on the uploaded CSV.
```

The system recognizes feature engineering intent from a range of natural language prompts.

**Don't have a cleaned CSV yet?** Skill B expects input that has already been through Skill A (Data Cleaning). If you haven't cleaned your data yet, start with Skill A first — upload your raw CSV and ask for data profiling and cleaning.

---

## Step 2 — Handoff Contract Validation

The system validates the uploaded CSV against the Skill A handoff contract. The user sees:

```
🔍 Validating input against Skill A handoff contract...
✅ File: sales_data_cleaned.csv — valid CSV
✅ Shape: 1,247 rows × 14 columns (17,458 cells)
✅ Column names: no duplicates, no special characters
✅ Types: consistent within each column
✅ Run ID: feature-20260406-091533-b2f1
ℹ️ Skill A transform metadata: found — provenance verified, PII flags loaded
ℹ️ Skill A transform report: found — context loaded

All checks passed. Starting feature engineering pipeline...
```

If optional files are not present:

```
ℹ️ Skill A transform metadata: not found — Skill B will run its own PII scan
ℹ️ Skill A transform report: not found — proceeding without Skill A context
```

If a hard gate fails:

```
❌ Handoff contract violation: column names contain special characters
   — "Sales Amount ($)", "Customer Name (Full)"
   Skill A should have standardized these. Please re-run Skill A
   or rename the columns manually and re-upload.
```

---

## Step 3 — PII Scan

The system checks for personally identifiable information. The user sees:

If PII flags were loaded from Skill A's JSON:
```
🔒 PII scan: loaded 3 flags from Skill A transform metadata
⚠️ Column 'customer_name' — Direct PII (names)
⚠️ Column 'email_address' — Direct PII (email)
⚠️ Column 'zip_code' — Indirect PII (postal code)

The LLM will note these columns when proposing features.
```

If running Skill B's own heuristic scan:
```
🔒 Running PII scan (heuristic — column names only)...
⚠️ Column 'customer_name' may contain Direct PII — names.
   Consider excluding this column from feature engineering.
⚠️ Column 'zip_code' may contain Indirect PII — postal code.
   Consider excluding this column from feature engineering.
✅ 12 of 14 columns clear.
```

If no PII detected:
```
🔒 PII scan complete.
✅ No potential PII detected in this dataset.
```

---

## Step 4 — Feature Engineering (Batch by Batch)

The system proposes and validates features in 6 batches. For each batch, the user sees the proposal, the persona challenges, and the outcome.

Each proposal is reviewed by three specialized reviewers before it's approved:
- **Feature Relevance Skeptic** — asks "is this feature actually useful, or is it redundant?"
- **Statistical Reviewer** — asks "is this method valid for this data?"
- **Domain Expert** — asks "does this make business sense?"

This review process is how the pipeline prevents bad or unnecessary features from being created.

**Batch 1 — Date/Time Extraction:**
```
📋 Batch 1: Date/Time Extraction
   Analyzing datetime columns...

   Proposed features:
   1. day_of_week — from 'order_date' — captures purchasing cyclicality
   2. hour_of_day — from 'order_date' — captures time-of-day patterns
   3. month — from 'order_date' — captures seasonal trends

   🔎 Feature Relevance Skeptic: All 3 approved — no redundancy concerns.
   🔎 Statistical Reviewer: All 3 approved — datetime extraction is
      straightforward for this column type.
   🔎 Domain Expert: All 3 approved — standard retail time features.

   ✅ Batch 1 complete: 3 features approved (confidence: 95/100, 95/100, 95/100)
```

**Batch 2 — Text Features:**
```
📋 Batch 2: Text Features
   Analyzing text columns...

   ℹ️ Skipped — no text columns suitable for feature extraction.
```

**Batch 3 — Aggregate Features:**
```
📋 Batch 3: Aggregate Features
   Analyzing grouping opportunities...

   Proposed features:
   1. net_sales_per_account — groupby 'account_id', sum 'sale_amount'
      "Normalizes total spend per account — without it, you can't
      distinguish high-value from low-value accounts."
   2. transaction_count_per_account — groupby 'account_id', count
      "Measures account activity level."
   3. avg_sale_per_account — groupby 'account_id', mean 'sale_amount'
      "Captures typical transaction size per account."

   🔎 Feature Relevance Skeptic: Approved 1 and 2. Challenged 3 —
      "avg_sale is derivable from net_sales / transaction_count.
      Adding it creates redundancy."
   🔎 Statistical Reviewer: Approved all 3 — methods are valid.
   🔎 Domain Expert: Agrees with Skeptic on 3 — "redundant metric."

   ⚠️ Feature 'avg_sale_per_account' rejected (redundant).
   ✅ Batch 3 complete: 2 features approved, 1 rejected
      (confidence: 95/100, 95/100)
```

**Batches 4–6** follow the same pattern. If a feature is rejected and an alternative is proposed:

```
   ⚠️ Feature 'price_to_median_ratio' rejected by Statistical Reviewer —
      "median is sensitive to the skewed distribution in this column."
   🔄 Alternative proposed: 'price_to_mean_ratio' — using mean instead.
   🔎 Personas reviewing alternative...
   ✅ Alternative approved (confidence: 67/100 — approved with caveats)
```

---

## Step 5 — Execution

After all batches are approved, the system executes the transformations. The user sees:

```
⚙️ Executing approved transformations...
   Batch 1: Date/Time Extraction — 3 features ✅
   Batch 2: Text Features — skipped
   Batch 3: Aggregate Features — 2 features ✅
   Batch 4: Derived Columns — 4 features ✅
   Batch 5: Categorical Encoding — 2 features ✅
   Batch 6: Normalization / Scaling — 3 features ✅

✅ All transformations executed. 14 new features created.
   Output shape: 1,247 rows × 28 columns (14 original + 14 engineered)
```

If an execution error occurs:

```
❌ Execution error in Batch 4: division by zero in 'revenue_per_unit'
   for 3 rows where 'units_sold' = 0.
   Action: replaced with NaN. Logged in mistake log.
   Continuing with remaining transformations...
```

---

## Step 6 — Verification

The Data Analyst persona reviews the output. The user sees:

```
🔎 Data Analyst verifying output...
   ✅ Row count preserved (1,247 → 1,247)
   ✅ Original columns unchanged
   ✅ All 14 engineered columns present with feat_ prefix
   ✅ No unexpected NaN values
   ✅ No infinity values
   ✅ Encoding mappings correct

✅ Verification complete — all checks passed.
```

If corrections are needed:

```
🔎 Data Analyst verifying output...
   ⚠️ feat_is_premium_category: one-hot encoding produced 4 binary
      columns but source column had 5 unique values — category
      'Unknown' was not encoded.
   ✅ Correction: added missing encoding for 'Unknown' category.

✅ Verification complete — 1 correction applied.
```

---

## Step 7 — Report and Dictionary Generation

The system generates the transformation report and data dictionary. The user sees:

```
📝 Generating transformation report...
🔍 Running jargon scan...
   ⚠️ 1 term flagged: "one-hot encoding" — explanation added.
✅ Jargon scan passed.
📝 Generating data dictionary...
✅ All outputs ready.
```

The transformation report is then delivered inline in the chat. For runs with more than 10 features, the inline version is a summary:

The data dictionary is also shown inline after the transformation report, so you can see what each feature means without downloading anything.

```markdown
# Feature Engineering Transformation Report

**Run ID**: feature-20260406-091533-b2f1
**Input File**: sales_data_cleaned.csv
**Input Shape**: 1,247 rows × 14 columns
**Output Shape**: 1,247 rows × 28 columns (14 features added)
**Confidence Score Range**: 67/100 – 95/100

---

## Summary

14 features proposed, 13 approved, 1 rejected. 1 batch skipped
(no text columns). All features executed and verified.

## Feature Summary

| Feature | Type | Source | Confidence |
|---------|------|--------|------------|
| feat_day_of_week | int64 | order_date | 95/100 |
| feat_hour_of_day | int64 | order_date | 95/100 |
| feat_month | int64 | order_date | 95/100 |
| feat_net_sales_per_account | float64 | account_id, sale_amount | 95/100 |
| feat_transaction_count | int64 | account_id | 95/100 |
| ... | ... | ... | ... |

(Full detail for all 14 features available in the download.)

## Rejected Transformations

### avg_sale_per_account (Rejected)
- **Rejected by:** Feature Relevance Skeptic, Domain Expert
- **Reason:** Redundant — derivable from net_sales / transaction_count

...
```

The data dictionary follows inline, then the download links.

---

## Step 8 — Download

The system presents downloadable files:

```
📥 Your feature engineering outputs are ready:
   • feature-20260406-091533-b2f1-engineered.csv
     — Feature-engineered dataset (14 original + 14 new columns)
   • feature-20260406-091533-b2f1-transformation-report.md
     — Full transformation report with all feature details
   • feature-20260406-091533-b2f1-data-dictionary.md
     — Data dictionary for all engineered features

Engineered columns are prefixed with 'feat_' — use
df.filter(like='feat_') to select them.
```

If errors occurred during the run:

```
ℹ️ A mistake log is also available for this run:
   • feature-20260406-091533-b2f1-mistake-log.md
```

---

## What to Do Next

- **Inspect features:** Open the CSV and review the `feat_` columns
- **Read the dictionary:** Check the data dictionary to understand each feature
- **Re-run with changes:** Upload the same CSV and ask Skill B to focus on specific feature types (e.g., "Only create aggregate features")
- **Ask questions:** Ask follow-up questions — e.g., "Why was avg_sale_per_account rejected?"

---

## Error Reference

| Error | Cause | What to Do |
|-------|-------|------------|
| Handoff contract violation: duplicate column names | Skill A didn't resolve duplicates | Re-run Skill A or rename columns manually |
| Handoff contract violation: special characters | Skill A didn't standardize names | Re-run Skill A or rename columns manually |
| Handoff contract violation: mixed types | Skill A didn't resolve type inconsistencies | Re-run Skill A or fix types manually |
| File is not a valid CSV | File is corrupted or wrong format | Re-upload or convert to CSV |
| Exceeds feature engineering limit | Dataset too large for sandbox | Reduce rows or columns |
| Execution error: division by zero | Derived feature hit zero denominator | Automatic — replaced with NaN, logged |
| Execution error: encoding failed | Unexpected category values | Pipeline stops, flags for review |
| Pipeline crashed mid-execution | Session state lost | Start new session, re-upload CSV |
| No feature engineering opportunities | Dataset has no suitable columns | Original CSV returned unchanged with report |

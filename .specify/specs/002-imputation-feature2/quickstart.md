# Data Transformation with Persona Validation — Phase 1 Quickstart

**Date**: 2026-04-08 | **Spec**: Feature 002 — Data Transformation | **Status**: Approved

---

## Purpose

Minimal end-to-end walkthrough of the simplest valid Data Transformation invocation. Shows exactly what a user does and what the system returns at each step. Assumes Feature 1 (Data Profiling) has already been completed in the same Claude.ai session.

---

## Prerequisites

- Feature 1 (Data Profiling) has completed successfully in the current Claude.ai session
- The profiling outputs are present in the sandbox: `{profiling_run_id}-summary.md`, `{profiling_run_id}-profiling-data.json`, and the original raw CSV
- No additional setup required — Feature 2 uses the same session, same libraries

---

## Step 1 — Request Data Cleaning

After Feature 1 completes, the user requests data cleaning in natural language. Examples:

```
Clean this dataset based on the profiling results.
Fix the issues you found in the data.
Apply data cleaning transformations.
```

The system recognizes cleaning intent from a range of natural language prompts — you don't need to use an exact phrase. You can request cleaning at any point during the session, as long as Feature 1 profiling has been completed. You don't need to request it immediately after profiling.

---

## Step 2 — Load Feature 1 Outputs

The system loads the profiling outputs from Feature 1. The user sees:

```
🔍 Loading profiling results...
✅ Profiling data loaded: profile-20260404-143022-a3f7
✅ Original CSV loaded: sales_data.csv (1,247 rows × 14 columns)
✅ Run ID: transform-20260408-091530-b2e1

Ready to analyze and propose transformations.
```

If Feature 1 outputs are missing:

```
❌ No profiling data found. Please run data profiling first —
   upload your CSV and ask for profiling before cleaning can begin.
```

---

## Step 3 — Transformation Proposal

The system analyzes the profiling data and proposes cleaning transformations. All 7 pipeline steps are listed — steps with no issues are marked as skipped. The user sees:

```
📋 Analyzing profiling results and proposing transformations...

Based on the profiling report, I recommend the following
data cleaning transformations:

Step 1 — Column Name Standardization
  • Rename 2 columns with special characters → snake_case
  Strategy: standardize_to_snake_case + remove_special_characters

Step 2 — Drop Empty Columns
  • Drop column "notes" (100% missing values)
  Strategy: drop_column

Step 3 — Type Resolution
  • Convert "zip_code" from mixed int/string → string
  Strategy: coerce_to_target_type (target: string)

Step 4 — Invalid Category Cleanup
  • No issues found — skipping

Step 5 — Missing Value Imputation
  • Impute "region" (12% missing) with "Unknown"
  • Impute "sales_amount" (3% missing) with median
  Strategy: impute_unknown, impute_median

Step 6 — Deduplication
  • Remove 47 exact duplicate rows (keep first occurrence)
  Strategy: drop_exact_keep_first

Step 7 — Outlier Treatment
  • No issues found — skipping

Submitting to review panel for validation...
```

---

## Step 4 — Persona Review Panel

The system runs the review panel. All-approved steps show as a single summary line. Only steps with medium/low confidence or rejections show expanded detail. The user sees:

```
🔎 Review panel evaluating proposed transformations...

Review panel results:

✅ Step 1 — Column names: APPROVED (95 — High)
✅ Step 2 — Drop "notes": APPROVED (95 — High)
✅ Step 3 — Type coercion: APPROVED (95 — High)
⚠️ Step 5 — Imputation: APPROVED with dissent (67 — Medium)
   Conservative view notes that imputing "region" at 12%
   missing is acceptable but should be flagged.
✅ Step 6 — Deduplication: APPROVED (95 — High)

All transformations approved. Proceeding to execution.
```

**If a transformation is rejected:**

```
❌ Step 5 — Imputation for "region": REJECTED
   Business view: Most-frequent imputation for a geographic
   field could introduce spatial bias.
   
   Alternative proposed: Impute with "Unknown" instead.
   Re-evaluating...

✅ Step 5 — Imputation for "region" (revised): APPROVED
   (82 — High) Imputing with "Unknown" preserves
   transparency about missing geographic data.
```

**If no consensus is reached (confidence = 35):**

```
⚠️ The review panel could not reach consensus on how to handle
   missing values in column "revenue" (34% missing).

   Column context: numeric measure, 34% missing, 892 unique values

   Perspectives:
   • Conservative view: 34% is too high for reliable imputation;
     dropping the column is safer.
   • Business view: Revenue is a critical metric — losing it
     entirely is worse than imputing.
   • Technical view: Median imputation at 34% will compress the
     distribution noticeably.

   Option 1: Impute with median (score: 35)
   — Preserves all rows; median is robust to outliers
   
   Option 2: Drop rows with missing revenue (score: 30)
   — Loses 34% of rows but avoids imputation assumptions
   
   Option 3: Skip this transformation
   — Column remains as-is; documented as unresolved

   Which would you prefer? You can pick a number, type "skip",
   or provide additional guidance.
```

The user responds (e.g., "1" or "skip" or "impute with median but flag it prominently"), and the pipeline continues.

---

## Step 5 — Transformation Execution

The system executes approved transformations in the fixed 7-step order. The user sees:

```
⚙️ Executing approved transformations...

Step 1: Standardizing column names... ✅
  • 2 columns renamed
Step 2: Dropping empty columns... ✅
  • 1 column dropped ("notes")
  ⚠️ Column removed from dataset
Step 3: Resolving type inconsistencies... ✅
  • "zip_code" converted to string
Step 5: Imputing missing values... ✅
  • "region": 150 values imputed with "Unknown"
  • "sales_amount": 37 values imputed with median (1,245.50)
  ⚠️ High-impact: 12.0% of values in "region" were imputed
     — exceeds the 10% threshold
Step 6: Removing duplicates... ✅
  • 47 duplicate rows removed

Execution complete. Running verification...
```

Note: User-facing messages may include summary statistics (like median values used for imputation) for transparency. These values do not appear in exported logs or files — only in the conversational output.

**If a transformation fails:**

```
❌ Transformation failed at step 3 (type_coercion):
   Could not convert column "price" — contains non-numeric
   values that cannot be coerced.
   
   Please try again in a new session.
```

---

## Step 6 — Data Analyst Verification

The system runs the Data Analyst persona verification. The user sees:

```
🔎 Verifying transformations...
✅ Row count: 1,247 → 1,200 (47 removed — matches deduplication)
✅ Column count: 14 → 13 (1 dropped — matches "notes" removal)
✅ No unapproved changes detected
✅ All transformation metrics consistent with approved plan
✅ No unexpected missing values introduced
✅ No new duplicate rows introduced

Verification complete — all checks passed.
```

**If the verification finds a discrepancy:**

```
🔎 Verifying transformations...
⚠️ Verification found a discrepancy: Row count is 1,195 but
   expected 1,200 after deduplication. 5 additional rows may
   have been removed unexpectedly.
   
   Please review the transformation report and consider
   re-running the pipeline.
```

---

## Step 7 — Report Generation and Jargon Scan

The system generates the transformation report and runs the jargon scan. The user sees:

```
📝 Generating transformation report...
🔎 Running jargon scan...
✅ Report complete — no jargon violations found.
```

**If jargon violations are found and corrected:**

```
📝 Generating transformation report...
🔎 Running jargon scan...
⚠️ 1 undefined term found: "IQR" — adding definition.
✅ Report complete — 1 term corrected.
```

---

## Step 8 — Report Delivery

The system delivers the transformation report inline. A truncated example:

```markdown
# Data Transformation Report

**Run ID**: transform-20260408-091530-b2e1
**Source Profiling Run**: profile-20260404-143022-a3f7
**File**: sales_data.csv
**Generated**: 2026-04-08T09:18:22Z

---

## Executive Summary

5 data cleaning transformations were applied across 4 pipeline
steps. The dataset was reduced from 1,247 to 1,200 rows (47
duplicates removed) and from 14 to 13 columns (1 empty column
dropped). All transformations were validated by the review panel
with confidence scores ranging from 67 to 95.

## Dataset Comparison

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Rows | 1,247 | 1,200 | -47 (-3.8%) |
| Columns | 14 | 13 | -1 |
| Missing cells | 2,031 (11.6%) | 0 (0%) | -2,031 |
| Duplicate rows | 47 (3.8%) | 0 (0%) | -47 |

## Transformations Applied

### Step 1: Column Name Standardization

**Rename columns to snake_case** (Confidence: 95/100 — High)

- **What was done**: 2 columns renamed to remove special
  characters and convert to snake_case format.
- **Why**: Non-standard column names cause errors in code that
  references columns by name and make the dataset harder to
  work with programmatically.
- **Impact**: Column names are now consistent and code-friendly.
  No data values were changed.

...

(Report continues with remaining steps, Next Steps,
Verification Summary, and Pipeline Log Summary.)
```

---

## Step 9 — Download

Immediately after the report, the system presents downloadable files:

```
📥 Your cleaning outputs are ready for download:
   • transform-20260408-091530-b2e1-cleaned.csv
     — Cleaned dataset (1,200 rows × 13 columns)
   • transform-20260408-091530-b2e1-transform-report.md
     — Transformation report (the report shown above)
   • transform-20260408-091530-b2e1-transform-metadata.json
     — Transformation metadata (for feature engineering
       and downstream processing)

A pipeline log (transform-20260408-091530-b2e1-mistake-log.json)
is also available if you need audit details.

Your data cleaning is complete. You can now proceed to
feature engineering, or download these files to share
with your team.
```

---

## What to Do Next

- **Proceed to feature engineering**: Ask "Engineer features for this cleaned dataset" to begin Skill B
- **Download and share**: Use the download links above to save the outputs
- **Re-run with different choices**: Upload the original CSV, re-run profiling, then request cleaning again — the LLM may propose different strategies
- **Review transformation details**: The transformation report documents every decision with full justification. Refer to the relevant step section for details on any specific transformation.

---

## Error Reference

| Error | Cause | What to Do |
|-------|-------|------------|
| No profiling data found | Feature 1 not run or outputs missing | Run Feature 1 first: upload CSV and request profiling |
| Profiling data incomplete or corrupted | JSON missing required keys | Re-run Feature 1 in a new session |
| Transformation failed at step {n} | Python error during execution | Start a new session, re-upload your CSV, and re-run the full pipeline (profiling → cleaning). Feature 1 outputs are session-bound and cannot be reused across sessions. Downloading outputs from Feature 1 is recommended as a backup before proceeding to cleaning. |
| Verification found a discrepancy | Output doesn't match expected state | Review the report; consider re-running |
| Pipeline crashed mid-execution | Session state lost | Start a new session and re-upload your CSV |
| Review panel could not reach consensus | Personas disagreed (score < 50) | Choose an option, skip, or provide guidance |

---

## No-Issues Workflow

If the profiling report found no data quality issues, the user sees a streamlined flow:

```
🔍 Loading profiling results...
✅ Profiling data loaded: profile-20260404-143022-a3f7

📋 Analyzing profiling results...
✅ No data quality issues detected in the profiling report.

🔎 Running light verification to confirm...
✅ Verified: data is clean. No transformations required.

📝 Generating report...

# Data Transformation Report

**Run ID**: transform-20260408-091530-b2e1
...

## Executive Summary

No data quality issues were identified in the profiling report.
A light verification confirmed that the data requires no cleaning
transformations. The original dataset is output unchanged.

## Next Steps — Recommended Additional Processing

The following transformations are recommended for the next stage
of data preparation (feature engineering):
- Normalization/standardization for numeric columns
- Encoding for categorical columns
...

📥 Your outputs are ready for download:
   • transform-20260408-091530-b2e1-cleaned.csv
     — Original dataset (unchanged — no cleaning required)
   • transform-20260408-091530-b2e1-transform-report.md
     — Transformation report confirming no cleaning needed
   • transform-20260408-091530-b2e1-transform-metadata.json
     — Metadata for downstream processing
```

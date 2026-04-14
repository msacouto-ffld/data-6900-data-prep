# Transformation Report Template (DM-109)

This file is the authoritative template for the Data Transformation
report produced by Feature 2 (`generate_report` → `scan_jargon` → `deliver_outputs`).

The `generate_report` LLM call uses this template as a structural
reference. The 10 sections listed below appear in the output report in
exactly this order. Sections 5, 6, and 7 are **omitted entirely** when
they have no content — they are not shown with a "None" placeholder.

Every transformation in section 4 MUST follow the **3-part template**
(What was done / Why / Impact) plus a confidence score and a before/after
metrics table. High-impact flags are inlined under the transformation
that triggered them.

---

```markdown
# Data Transformation Report

**Run ID**: {transform_run_id}
**Source Profiling Run**: {source_profiling_run_id}
**File**: {original_filename}
**Generated**: {timestamp}

---

## Executive Summary

{2–3 sentences describing what was done at a high level:
 - How many transformations were applied, across how many steps
 - Net change in row count and column count
 - Range of confidence scores (e.g., "67 to 95")
 - Any notable edge cases (human review, skipped steps, no-issues path)}

---

## Dataset Comparison

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Rows | {n_rows_before} | {n_rows_after} | {delta_rows} ({delta_rows_pct}%) |
| Columns | {n_cols_before} | {n_cols_after} | {delta_cols} |
| Missing cells | {n_missing_before} ({pct_missing_before}%) | {n_missing_after} ({pct_missing_after}%) | {delta_missing} |
| Duplicate rows | {n_dup_before} ({pct_dup_before}%) | {n_dup_after} ({pct_dup_after}%) | {delta_dup} |

---

## Transformations Applied

{One subsection per step that has approved transformations. Steps with
 no transformations are NOT shown in this section — they simply don't
 appear. Within each step, each transformation follows the 3-part
 template shown below.}

### Step {N}: {Step Name}

**{Transformation title — usually the strategy name in plain language}**
(Confidence: {score}/100 — {band})

- **What was done**: {description of the action — columns affected,
  values changed, parameters used}
- **Why**: {the reasoning — what problem this transformation solved,
  why this strategy was chosen over alternatives}
- **Impact**: {what changed in the dataset — count of values modified,
  rows affected, side effects}

| Column | Metric | Before | After |
|--------|--------|--------|-------|
| {col} | {n_missing / dtype / n_unique / mean / etc.} | {before} | {after} |

{If the transformation triggered a high-impact flag, include it inline:}

> ⚠️ **High-impact flag**: {condition name} — actual value
> {value} exceeds threshold of {threshold}. {Plain-language
> explanation of why this matters.}

---

## Rejected Transformations

{OMIT THIS SECTION ENTIRELY if no transformations were rejected.}

{Table of transformations that were rejected by the review panel,
 with the alternative that was ultimately adopted.}

| Step | Original Strategy | Rejection Reason | Alternative Adopted |
|------|-------------------|------------------|---------------------|
| {n} | {strategy} | {reason from DM-105} | {alternative from DM-106} |

---

## Skipped Transformations

{OMIT THIS SECTION ENTIRELY if no transformations were skipped.}

{Transformations where no consensus was reached and the user chose to
 skip. Each entry includes the column context the user saw.}

### {Step N} — {Issue description}

- **Affected columns**: {list}
- **Why skipped**: {reason — user_skipped or user_guided fallback}
- **User input**: {what the user typed, if any}
- **Status**: Column(s) remain as-is. Documented as unresolved for
  downstream review.

---

## High-Impact Summary

{OMIT THIS SECTION ENTIRELY if no flags were triggered.}

{Consolidated list of all high-impact flags across the whole pipeline.
 Even when individual flags appeared inline under their transformations
 in section 4, they are re-summarised here for audit.}

| Step | Condition | Value | Threshold | Affected Columns |
|------|-----------|-------|-----------|------------------|
| {n} | {row_reduction / imputation_pct / mean_shift / etc.} | {actual} | {threshold} | {columns} |

---

## Next Steps — Recommended Additional Processing

The following transformations are recommended for the next stage of
data preparation. They are **out of scope for Skill A (data cleaning)**
and are handled by Skill B (feature engineering):

- **Normalization / standardization** for numeric columns with wide
  value ranges
- **Encoding** for categorical columns (one-hot, label, or target
  encoding depending on use case)
- **Feature engineering** — derived columns, aggregations, date/time
  feature extraction, text features
- **Dimensionality reduction** — if any columns have very high
  cardinality after encoding

These are not defects in the cleaned dataset — they are the natural
next step once the dataset is clean.

---

## Verification Summary

**Review Status**: {PASS | CORRECTIONS APPLIED | DISCREPANCY FOUND}

**Confirmed Accurate:**
{- List of claims the Data Analyst persona verified against step_results}

**Corrections Made:**
{- List of corrections applied to the draft report during verification
 - Or "None" if no corrections were needed}

**Discrepancies Found:**
{OMIT if status is PASS or CORRECTIONS APPLIED.
 Otherwise: list of discrepancies the persona flagged that could not
 be auto-corrected. Each discrepancy includes a recommendation for
 the user.}

---

## Pipeline Log Summary

The full audit trail is available in `{transform_run_id}-mistake-log.json`.
Entry counts by type from this run:

| Event Type | Count |
|------------|-------|
| persona_rejection | {n} |
| execution_error | {n} |
| edge_case_warning | {n} |
| consensus_failure | {n} |
| high_impact_flag | {n} |
| human_review_decision | {n} |

{If the total count is 0, state: "The pipeline completed with no logged
 events beyond normal execution. All transformations proceeded
 as planned."}
```

---

## No-Issues Report Variant

When the pipeline takes the light-verification fast-path (FR-121),
the report is simplified. It still uses this template but with the
following adjustments:

- **Executive Summary** states: *"No data quality issues were identified
  in the profiling report. A light verification confirmed that the
  dataset requires no cleaning transformations. The original dataset
  is output unchanged."*
- **Dataset Comparison** — before and after columns are identical
- **Transformations Applied** — replaced with the single line:
  *"No transformations were applied. The dataset is clean."*
- **Rejected Transformations**, **Skipped Transformations**,
  **High-Impact Summary** — all omitted
- **Next Steps** — same content as the standard report
- **Verification Summary** — PASS with the light-verification confirmation
- **Pipeline Log Summary** — entry counts will typically show 0 or 1
  (the `edge_case_warning: no_issues_path_triggered` event)

---

## Template Compliance Checklist

When the report is generated, the `generate_report` LLM call MUST
ensure all of the following hold. `verify_output` + `scan_jargon`
check these downstream.

- [ ] Sections appear in the exact order listed above
- [ ] Sections 5, 6, 7 are omitted (not included as empty) when they
      have no content
- [ ] Every transformation in section 4 has all three parts of the
      template (What / Why / Impact)
- [ ] Every transformation shows a confidence score from the fixed set
      (95, 82, 67, 50, 35) and its band
- [ ] Every high-impact flag shows both the actual value AND the threshold
- [ ] No raw data values appear anywhere in the report (column names and
      aggregate statistics only)
- [ ] Method-specific terms (z-score, IQR, winsorize, etc.) are explained
      on first use
- [ ] All acronyms are defined on first use
- [ ] Dataset Comparison numbers come from the script-captured
      `metrics_before` / `metrics_after`, never from LLM estimation
- [ ] Rejected / Skipped transformations are reported faithfully even
      when they contain user-facing friction (don't hide rejections to
      make the pipeline look cleaner)

---

## References

- **DM-109** — this template, authoritative source
- **DM-107** — step execution results that feed the Transformations Applied section
- **DM-108** — high-impact thresholds shown in the flag annotations
- **DM-112** — mistake log referenced in the Pipeline Log Summary section
- **FR-109** through **FR-112** — functional requirements for report content
- **FR-118**, **FR-119** — privacy and plain-language constraints

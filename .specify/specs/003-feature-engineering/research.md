# Feature Engineering with Persona Validation — Phase 0 Research

**Date**: 2026-04-06 | **Spec**: Feature 003 — Feature Engineering | **Status**: Draft

## Purpose

This document identifies all open technical questions that must be resolved before design begins. For each question, it states the options and recommends an answer with rationale. Approved answers become inputs to Phase 1 (data-model.md, quickstart.md, contracts/).

---

## RQ-001 — Handoff Contract Validation Strategy

**Question:** What exactly must Skill B validate about Skill A's output before proceeding, and how is the validation implemented?

**Proposed Contract — Skill B validates:**

| Check | Rule | How Validated |
|-------|------|---------------|
| File format | Valid CSV, parseable by `pd.read_csv()` | Hard gate — pandas parse attempt |
| No duplicate column names | `df.columns.duplicated().any()` returns False | Hard gate — pandas check |
| Clean column names | All columns match `r'^[a-zA-Z_][a-zA-Z0-9_]*$'` | Hard gate — regex scan |
| Consistent types per column | Each column has a single pandas dtype — no object-type columns with mixed underlying types | Hard gate — for columns with dtype `object`, check `pd.api.types.infer_dtype(col, skipna=True)` returns a consistent type (not "mixed" or "mixed-integer") |
| Missing values handled | Either no missing values, or Skill A's transformation report documents and justifies remaining missing values | Soft gate — if missing values exist AND no transformation report is present, warn but proceed; if transformation report is present, check that missing columns are documented |
| Run ID traceability | Skill A's run ID is present (in profiling-data.json if available) | Informational — logged for traceability but not a hard gate |

**Optional inputs (read if available, not required):**

| Input | What Skill B Gets From It |
|-------|---------------------------|
| profiling-data.json | PII flags, profiling statistics, quality detections — saves Skill B from re-detecting |
| Transformation report (.md) | Context on what Skill A did — informs smarter feature suggestions |

**Validation failure behavior:**
- Hard gate failure → Skill B stops immediately, identifies the specific violation, and flags for human review (FR-202)
- Soft gate warning → Skill B proceeds but logs the warning in the mistake log
- If a CSV was not produced by Skill A (e.g., user uploads a raw CSV directly), Skill B cannot detect this with certainty. It validates the contract checks above — if they pass, Skill B proceeds regardless of origin.

**Recommendation:** This contract design. The hard gates catch the issues Skill A is supposed to fix. The soft gate on missing values is pragmatic — Skill A might legitimately leave some missing values with documented justification. The optional inputs give Skill B a boost without creating a hard dependency.

---

## RQ-002 — PII Re-Check Strategy

**Question:** How does Skill B check for PII before running feature engineering?

**Options:**

| Option | Approach | Trade-off |
|--------|----------|-----------|
| A | Full two-layer scan (heuristic + LLM value inspection) — same as Skill A | Thorough but expensive; duplicates Skill A's work |
| B | Lightweight column-name heuristic only — no LLM value inspection | Fast and cheap; relies on Skill A having done the thorough scan already |
| C | Read PII flags from profiling-data.json if available; run heuristic scan if not | Best of both — gets full PII data when available, falls back gracefully |

**Recommendation:** Option C. When profiling-data.json is present, Skill B reads Skill A's PII flags directly — no re-scanning needed. When absent, Skill B runs a lightweight column-name heuristic (word-boundary matching against a token list of PII-indicative terms). No LLM value inspection in either case — Skill B's PII check is a safety net, not the primary detection.

**Heuristic token list (same as Skill A's Layer 1):**

| PII Type | Match Tokens |
|----------|-------------|
| direct_name | name, first_name, last_name, full_name, surname, customer_name, person |
| direct_contact | email, phone, telephone, mobile, cell, address, street, city, state, country |
| direct_identifier | ssn, social_security, passport, driver_license, national_id, license_number |
| indirect | dob, date_of_birth, birth_date, birthday, zip, zip_code, postal_code, job_title, occupation, age, gender, sex, race, ethnicity, religion |
| financial | account_number, account_no, credit_card, card_number, routing_number, iban, transaction_id, bank, salary, income |

**Warning format:** Same as Skill A's format for consistency, with actionable guidance:
```
⚠️ PII Warning: Column '{column_name}' may contain {PII_type} PII
   ({detection_source}). Consider excluding this column from feature
   engineering, or ensure any derived features do not expose
   individual-level PII.
```

**PII and feature engineering:** If PII is detected (from JSON or heuristic), Skill B warns the user but does not automatically exclude PII columns from feature engineering. The LLM should note PII-flagged columns in its proposals, and the Domain Expert persona should challenge any features derived from PII columns.

---

## RQ-003 — Persona Validation Loop Architecture

**Question:** How should the four-persona validation system be implemented within Claude.ai sessions?

**Options:**

| Option | Approach | Trade-off |
|--------|----------|-----------|
| A | Single LLM call — all three challenge personas in one prompt | Cheapest; but LLM juggles three roles, surface-level review |
| B | Three separate LLM calls — one per challenge persona, each with narrow system prompt and checklist | Best hallucination prevention; higher token cost |
| C | Two calls — combine Feature Relevance Skeptic + Domain Expert into one, Statistical Reviewer separate | Middle ground; but loses focus of individual roles |

**Recommendation:** Option B — three separate LLM calls for the challenge loop, plus one for the Data Analyst post-execution verification. Four total persona calls per batch.

**Persona specifications:**

| Persona | Phase | Specific Job | Checks Against |
|---------|-------|-------------|----------------|
| Feature Relevance Skeptic | Challenge loop | Is this feature redundant? Does it add info beyond existing columns? | Correlation with existing columns. If proposed feature would be >0.95 correlated with an existing column, challenge it. |
| Statistical Reviewer | Challenge loop | Is this method valid for this data's distribution and type? | Actual column stats — skewness, cardinality, variance. Catches zero-variance normalization, high-cardinality one-hot, etc. |
| Domain Expert | Challenge loop | Does this make business sense? Would a data scientist use this? | Synchrony-style metric patterns. Catches zero-denominator ratios, meaningless derived features. |
| Data Analyst | Post-execution | Did the transformations produce what was expected? | Before/after comparison of actual data. Catches NaN, infinity, wrong encodings, missing columns, row count changes. |

**Each persona receives:**
- The cleaned CSV summary statistics (column types, row count, basic stats)
- The proposed feature batch being evaluated
- Profiling data from Skill A (if available)
- Its specific checklist

**Rejection handling (FR-207):** If any challenge persona rejects a proposed feature, the LLM generates the next best alternative with justification. The alternative goes through the same persona loop. Maximum 2 rejection cycles per feature — after that, the feature is dropped and the rejection is logged in the mistake log.

**Approved feature tracking between batches:** The pipeline maintains a running list of approved features from all completed batches. Each new batch's proposal call receives this list so the LLM knows what's already been approved. This prevents later batches from proposing features that depend on rejected features, and enables the LLM to build on features approved in earlier batches (e.g., Batch 4 can propose a ratio using a column created in Batch 1).

---

## RQ-004 — Feature Proposal Batching Strategy

**Question:** Should the LLM propose all features at once, one at a time, or in batches?

**Options:**

| Option | Approach | Trade-off |
|--------|----------|-----------|
| A | All features in one call | Cheapest; highest hallucination risk — LLM proposes 15 features and some are poorly thought out |
| B | One feature at a time | Most thorough; extremely expensive — 15 features × 3 personas = 45+ LLM calls |
| C | Batch by transformation type | Balanced — each batch is focused, matches execution order, manageable number of calls |

**Recommendation:** Option C — batch by transformation type. Each batch goes through its own persona loop before the next batch is proposed.

**Batch sequence (matches execution order from RQ-005):**

| Batch | Transformation Type | What the LLM Proposes |
|-------|--------------------|-----------------------|
| 1 | Date/time extraction | day_of_week, hour, month, quarter, etc. from datetime columns |
| 2 | Basic text features | string_length, word_count, regex pattern flags from text columns |
| 3 | Aggregate features | groupby + transform metrics (sums, counts, averages per group) |
| 4 | Derived columns / ratios | Ratios, differences, interactions between numeric columns |
| 5 | Categorical encoding | One-hot, label encoding decisions per categorical column |
| 6 | Normalization / scaling | Min-max, z-score decisions per numeric column |

**Per batch, the LLM call sequence is:**
1. LLM proposes features for this batch type (1 call)
2. Feature Relevance Skeptic reviews (1 call)
3. Statistical Reviewer reviews (1 call)
4. Domain Expert reviews (1 call)
5. If rejections → LLM proposes alternatives (1 call) → personas review again (up to 2 rejection cycles)
6. Approved features for this batch are recorded

**After all 6 batches are approved:**
7. All approved features are executed in batch order (script)
8. Data Analyst persona verifies the full output (1 call)

**Empty batches:** If the dataset has no datetime columns, Batch 1 is skipped. If no text columns, Batch 2 is skipped. The LLM explicitly notes skipped batches and why.

**Aggregate proposal cap (Batch 3):** Aggregate features can multiply quickly — 3 grouping keys × 4 aggregation functions = 12 features. To keep the persona loop manageable, Batch 3 is capped at 10 proposed features. If the LLM identifies more than 10 aggregate opportunities, it proposes the top 10 by expected analytical value and notes the remainder as deferred. Deferred aggregates can be requested by the user in a follow-up.

---

## RQ-005 — Transformation Execution Order

**Question:** In what order should approved transformations be applied?

**Recommendation:** Fixed order, matching the proposal batch sequence:

1. **Date/time extraction** — creates new columns from datetime columns; originals untouched
2. **Basic text features** — creates new columns from text columns; originals untouched
3. **Aggregate features** (groupby + transform) — needs raw numeric values for accurate sums/counts
4. **Derived columns / ratios** — may reference columns created in steps 1–3
5. **Categorical encoding** — may create many new columns; happens after derived features that use original categorical values
6. **Normalization / scaling** — always last; changes numeric values, so anything computed after would use scaled numbers

**Rationale:** Create new information first, transform representations last. Each step may depend on columns created in previous steps but never on columns modified by later steps.

**Implementation:** The execution script applies transformations in this exact order. The transformation report documents the order with dependency reasoning so a data scientist understands why feature X was created before feature Y.

---

## RQ-006 — Aggregate Feature Implementation

**Question:** How does Skill B implement group-level aggregate metrics (like the Synchrony-style metrics) as row-level columns?

**Approach:** pandas `groupby().transform()` pattern. This computes the aggregate at the group level and maps it back to every row in the group, preserving the original DataFrame's row count.

**Example:**
```python
# Efficient pattern: compute all aggregates at once, then merge back
agg_df = df.groupby('account_id')['net_sale_amount'].agg(
    feat_net_sales_per_account='sum',
    feat_avg_sale_per_account='mean',
    feat_transaction_count_per_account='count'
).reset_index()

df = df.merge(agg_df, on='account_id', how='left')
```

This `groupby().agg()` + merge pattern is more efficient than calling `transform()` multiple times — it computes all aggregates for a grouping key in a single pass.

**How the LLM determines grouping keys:** The LLM infers grouping keys from the data — it looks at column names and types and proposes combinations. For example, it sees `account_id` (likely an identifier column with repeated values) and `sale_amount` (numeric) and proposes "group by account_id, sum sale_amount." The Domain Expert persona challenges whether the grouping makes business sense.

**Edge cases:**
- Grouping key has all unique values (every row is its own group) → aggregate equals the individual value → persona should catch this as a useless feature
- Grouping key has a single value (all rows in one group) → aggregate is a constant → persona should catch this as zero-variance
- Division-based aggregates (e.g., sales per active) → denominator could be zero → execution script replaces division-by-zero results with NaN, logged in transformation report

---

## RQ-007 — Confidence Score System

**Question:** What scale and criteria should confidence scores use?

**Recommendation:** 1–5 ordinal scale, justified by persona loop outcomes.

| Score | Label | When Assigned |
|-------|-------|---------------|
| 5 | Strong consensus | All three challenge personas approved, no challenges raised |
| 4 | Approved with minor note | All approved, one minor question raised and resolved |
| 3 | Approved with caveats | Substantive concerns raised and addressed |
| 2 | Weakly approved | Unresolved concerns — feature included with documented risk |
| 1 | Contested | Original rejected, alternative adopted — limited confidence in alternative |

**How it appears in the report:**
```
**Feature: feat_revenue_per_unit**
**Confidence: 4/5**
All personas approved. The Statistical Reviewer flagged that 3 rows
have a zero denominator — these are handled by replacing with NaN.
```

**Score assignment:** Each challenge persona returns a structured response that includes: `approved: true/false`, `challenges_raised: [list]`, `challenges_resolved: [list]`. The pipeline script parses these structured responses and assigns the score deterministically:

- 0 challenges raised → 5/5
- Challenges raised, all resolved, no lingering notes → 4/5
- Challenges raised, all resolved, with lingering caveats documented → 3/5
- Challenges raised, not all fully resolved → 2/5
- Original rejected, alternative adopted → 1/5

This keeps scoring objective — it's based on what happened in the loop, not the LLM rating its own confidence.

---

## RQ-008 — Jargon Scan Implementation

**Question:** How should FR-224 (automated jargon scan) be implemented?

**Recommendation:** Two layers.

**Layer 1 — Script with maintained term list (~15–20 terms):**
Runs before the verification persona. A Python script scans the transformation report and data dictionary for technical terms that require plain-language explanation.

**Initial term list:**
```python
JARGON_TERMS = [
    "one-hot encoding", "label encoding", "min-max scaling", "z-score",
    "standard deviation", "normalization", "standardization", "variance",
    "cardinality", "dimensionality", "dummy variable", "feature extraction",
    "imputation", "interpolation", "ordinal", "nominal", "categorical",
    "continuous", "discrete", "skewness", "kurtosis", "correlation",
    "multicollinearity", "outlier detection"
]
```

**Scan logic:** For each term found in the report, the script checks whether a plain-language explanation appears within the same section (within ~200 words of the term). If not, it flags the term. Flagged terms are passed to the LLM, which rewrites those specific sections to include explanations.

**Layer 2 — Verification persona (Data Analyst):**
The Data Analyst persona's checklist already includes plain language compliance (FR-007). After the script fixes known terms, the persona catches unexpected jargon the script missed.

**Term list maintenance:** New terms discovered by the verification persona or reported by users are added to the script's term list via the mistake log → constitution update cycle.

---

## RQ-009 — Column Naming Convention

**Question:** What naming convention should Skill B use for engineered columns?

**Recommendation:** All engineered columns prefixed with `feat_`, using snake_case.

**Convention rules:**
- Prefix: `feat_` — enables filtering with `df.filter(like='feat_')`
- Body: descriptive snake_case — `revenue_per_unit`, `day_of_week`, `is_premium`
- Full examples: `feat_revenue_per_unit`, `feat_day_of_week`, `feat_is_premium_category`

**Prefix application:** The execution script adds the `feat_` prefix during column creation. The LLM proposes feature names without the prefix (e.g., "revenue_per_unit"). This keeps the persona loop discussion clean and the prefix application consistent.

**Data dictionary entries:** Use the prefixed name as the official feature name. The "source columns" field references the original (non-prefixed) column names.

---

## RQ-010 — Benchmark Comparison Definition

**Question:** What does "benchmark comparison" mean concretely for each proposed feature (FR-204)?

**Recommendation:** A plain-language justification of analytical value, grounded in what the feature enables and what you'd lose without it. Not a statistical test — a reasoned argument that personas challenge.

**Per feature type:**

| Feature Type | Benchmark Comparison Must Include |
|--------------|----------------------------------|
| Derived column / ratio | Why this combination adds info beyond source columns individually. What you'd lose without it. |
| Aggregate (groupby) | Why the grouping level is analytically useful. What question it answers that individual rows can't. |
| Date/time extraction | What time-based pattern it enables. What cyclicality or seasonality it captures. |
| Categorical encoding | Why this encoding method over alternatives. What downstream models need from it. |
| Normalization / scaling | Why scaling is needed. What would go wrong without it (e.g., feature dominance in distance-based models). |
| Text feature | What signal it extracts. What proxy it serves for data quality or content characteristics. |

**Example:**
```
Feature: feat_revenue_per_unit
Benchmark: Revenue per unit normalizes for order size. Without it,
a $500 order of 100 items and a $500 order of 1 item look identical —
but they represent very different purchasing behaviors. This metric is
a standard retail KPI used by Synchrony and similar financial services
companies to assess transaction quality.
```

---

## RQ-011 — Mistake Log Implementation

**Question:** How should Skill B's mistake log be structured and maintained?

**Recommendation:** Append-as-you-go markdown file written throughout pipeline execution.

**Filename:** `{run_id}-mistake-log.md`

**Events logged:**

| Event Type | When Logged | What's Recorded |
|------------|-------------|-----------------|
| Handoff contract violation | Input validation | Which check failed, affected columns |
| PII warning | PII re-check | Column name, PII type, detection source |
| Persona rejection | Challenge loop | Which persona, which feature, reason, alternative proposed |
| Edge case triggered | Any pipeline step | Which case (zero-variance, high-cardinality, NaN/infinity, etc.), how handled |
| Execution error | Transformation execution | Which transformation, error type, whether pipeline halted |
| Verification correction | Data Analyst review | What was corrected in the report |
| Jargon scan flag | Jargon scan | Which term, where in report, whether fixed |

**Log entry format:**
```markdown
### [{timestamp}] {event_type}

**Step:** {pipeline_step}
**Details:** {description}
**Action taken:** {what the pipeline did}
**Columns involved:** {column names — never raw data values}
```

**Privacy:** The log must never contain raw data values (FR-222). Column names and aggregate statistics are permitted. All identifiers are masked or hashed.

**Implementation:** A Python function `log_event(log_path, event_type, step, details, action, columns)` appends a formatted entry to the file. Called from every pipeline step where loggable events can occur.

---

## RQ-012 — Output Delivery Mechanism

**Question:** How should Skill B's three outputs (CSV, transformation report, data dictionary) plus the mistake log be delivered?

**Recommendation:** Same pattern as Skill A — files written to Claude.ai sandbox filesystem and presented for download.

**Files produced:**

| File | Format | Filename |
|------|--------|----------|
| Feature-engineered CSV | .csv | `{run_id}-engineered.csv` |
| Transformation report | .md | `{run_id}-transformation-report.md` |
| Data dictionary | .md | `{run_id}-data-dictionary.md` |
| Mistake log | .md | `{run_id}-mistake-log.md` |

**Delivery sequence:**
1. Transformation report delivered inline in chat (with key highlights)
2. Data dictionary delivered inline in chat
3. Three primary files presented for download (CSV, report, dictionary)
4. Follow-up message: "Your feature engineering outputs are ready for download. The CSV contains both original and engineered columns (engineered columns are prefixed with `feat_`). The transformation report documents every decision. The data dictionary describes every new feature."
5. Mistake log is not presented proactively — it is an operational artifact for the PM. If the user asks for it, or if errors occurred during the run, the pipeline notes: "A mistake log for this run is also available: `{run_id}-mistake-log.md`"

**Inline delivery:** The full transformation report and data dictionary are shown in chat. For large reports (many features), the inline version may be truncated with a note: "Full report available in the download."

---

## RQ-013 — No-Opportunity Case (FR-225)

**Question:** How does the pipeline handle datasets where no feature engineering opportunities exist?

**Recommendation:** Abbreviated persona loop to confirm the finding, then output original CSV unchanged with an explanatory report.

**Mechanics:**

**Fast-path (structural impossibility):** If the dataset has ≤2 columns OR every column is a unique identifier (all values unique), the pipeline skips the persona loop entirely. The LLM generates the "no opportunity" report directly, and the Data Analyst confirms output equals input. This avoids burning 4 LLM calls on cases where feature engineering is structurally impossible.

**Standard path (all other cases):**
1. LLM analyzes the dataset and proposes "no features to engineer"
2. Feature Relevance Skeptic asks: "Are you sure? No date columns, no categorical columns, no numeric pairs worth combining?"
3. Statistical Reviewer asks: "Are there any distributional patterns that suggest useful transformations?"
4. Domain Expert asks: "Would a data scientist working with this data want any derived features?"
5. If all three agree → approved as "no opportunities" with confidence score (likely 5/5 if unanimous)

**Both paths produce:**
6. Original CSV output unchanged
7. Transformation report contains single entry:
   - **What:** No feature engineering transformations were applied
   - **Why:** {specific reason — e.g., all columns are identifiers, single column, no meaningful combinations}
   - **Impact:** Output CSV is identical to input
8. Data dictionary is empty or states "No engineered features"
9. Data Analyst persona confirms output CSV equals input CSV (equality check)

---

## Open Questions Deferred to Phase 1

| ID | Question | Deferred To |
|----|----------|-------------|
| D1 | Exact schema for persona prompt/checklist content | contracts/ |
| D2 | Transformation report markdown template — section order and field layout | data-model.md |
| D3 | Data dictionary markdown template — field layout per feature | data-model.md |
| D4 | Exact user invocation syntax | quickstart.md |
| D5 | Per-step input/output/error contract details | contracts/ |
| D6 | How the inline report handles very large feature sets (20+ features) | data-model.md |

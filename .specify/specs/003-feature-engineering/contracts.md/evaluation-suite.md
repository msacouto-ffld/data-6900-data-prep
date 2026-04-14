# Feature Engineering with Persona Validation — Phase 1 Contracts

**Date**: 2026-04-06 | **Spec**: Feature 003 — Feature Engineering | **Status**: Draft

---

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

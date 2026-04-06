# Evaluation Suite: V1 Minimum

**Coverage:** User Stories P1 (1, 2, 3) and P2 (4) | **Format:** Structured .md files

## Purpose

Four evaluation cases ensuring the profiling pipeline meets the spec's acceptance scenarios and the constitution's edge-case requirements. Each evaluation defines a fixed input set, invocation, expected behavior, and binary pass criteria.

---

## eval-001 — Generate Data Profile Report (User Story 1)

**Fixed Input Set:**

- CSV: Synthetic dataset with known issues — 500 rows × 12 columns
  - 2 columns with >20% missing values
  - 1 column with 100% missing values
  - 1 column with mixed types (integers and strings)
  - 2 numeric columns with outliers
  - Standard column names (no special characters, no duplicates)
  - No PII columns

**Invocation:** Upload CSV → "Profile this dataset and tell me what you find."

**Pass Criteria:**

| # | Criterion | Pass Condition |
|---|-----------|---------------|
| 1 | HTML report generated | ydata-profiling HTML file exists and is >0 bytes |
| 2 | NL report generated | Markdown report delivered inline with all 7 sections present |
| 3 | Missing values reported | NL report identifies the 3 columns with missing values and states correct percentages (±1% tolerance) |
| 4 | All-missing column flagged | NL report identifies the 100%-missing column as Critical |
| 5 | Mixed types reported | NL report identifies the mixed-type column |
| 6 | Outliers mentioned | NL report mentions outliers in the relevant numeric columns |
| 7 | No fabricated issues | NL report does not claim issues that don't exist in the data |
| 8 | Plain language | No undefined acronyms; no unexplained method-specific terms |
| 9 | Charts present | At least 2 of 3 charts displayed inline (missing values + dtypes) |
| 10 | Verification Summary | Section present with PASS or CORRECTIONS APPLIED status |
| 11 | Downloads available | HTML report and markdown summary available for download |
| 12 | Run ID present | Report header contains a valid run ID in the correct format |

**Fail Indicators:** Missing sections, incorrect percentages, fabricated issues, undefined jargon, no charts.

---

## eval-002 — Detect and Flag PII (User Story 2)

**Fixed Input Set:**

- CSV: Synthetic dataset — 200 rows × 10 columns
  - Column `customer_name`: synthetic names (Direct PII)
  - Column `email`: synthetic email addresses (Direct PII)
  - Column `zip_code`: 5-digit postal codes (Indirect PII)
  - Column `account_number`: synthetic account numbers (Financial PII)
  - Column `field_7`: contains phone-number-formatted strings but has a non-descriptive name (tests Layer 2 LLM detection)
  - Remaining columns: numeric data with no PII

**Invocation:** Upload CSV → "Profile this dataset."

**Pass Criteria:**

| # | Criterion | Pass Condition |
|---|-----------|---------------|
| 1 | Direct PII flagged | `customer_name` and `email` flagged as Direct PII |
| 2 | Indirect PII flagged | `zip_code` flagged as Indirect PII |
| 3 | Financial PII flagged | `account_number` flagged as Financial PII |
| 4 | LLM detection | `field_7` flagged as potential PII via value pattern (Layer 2). **Expected but may vary** — consistent failure indicates a prompt engineering issue, not a code bug. |
| 5 | No false negatives | All 5 PII columns flagged — zero misses (criterion 4 excluded from strict count if LLM variability applies) |
| 6 | Clean columns clear | Remaining 5 numeric columns not flagged |
| 7 | Warning format | Each warning follows the ⚠️ format from RQ-005 |
| 8 | No raw values | PII warnings contain column names and categories only — no actual data values |

**Fail Indicators:** Any PII column not flagged (except criterion 4 variability); non-PII column flagged; raw data values in warnings.

---

## eval-003 — Handle Edge Cases (User Story 3)

**Fixed Input Set:** Five separate CSVs, each tested independently:

| CSV | Description | Expected Behavior |
|-----|------------|------------------|
| edge-empty.csv | Headers only, no rows | Hard error: "This CSV contains headers but no data rows." No report generated. |
| edge-single-row.csv | 1 header + 1 data row, 5 columns | Proceeds. NL report includes Statistical Limitations section. |
| edge-duplicate-cols.csv | 8 columns, 2 pairs with duplicate names | Proceeds. NL report flags duplicate column names. |
| edge-special-chars.csv | Columns named "Sales $", "Name (Full)", "📧 Email" | Proceeds. NL report flags special characters in column names. |
| edge-not-csv.txt | A text file with prose, not tabular data | Hard error: "This file is not a valid CSV." No report generated. |

**Pass Criteria:**

| # | Criterion | Pass Condition |
|---|-----------|---------------|
| 1 | Empty CSV rejected | Error message displayed; no profiling report generated |
| 2 | Single-row processed | Profiling completes; Statistical Limitations section present |
| 3 | Duplicate columns flagged | NL report identifies which column names are duplicated |
| 4 | Special characters flagged | NL report identifies non-standard column names |
| 5 | Non-CSV rejected | Error message displayed; no profiling report generated |
| 6 | Error messages actionable | All error messages tell the user what to do to fix the issue |

**Fail Indicators:** Edge case not caught; silent failure; vague error message; pipeline crash without error.

---

## eval-004 — Download Profiling Outputs (User Story 4)

**Fixed Input Set:**

- CSV: Same synthetic dataset as eval-001

**Invocation:** Upload CSV → "Profile this dataset." → After report delivery, check downloads.

**Pass Criteria:**

| # | Criterion | Pass Condition |
|---|-----------|---------------|
| 1 | HTML report downloadable | `{run_id}-profile.html` available for download and opens in browser |
| 2 | Markdown summary downloadable | `{run_id}-summary.md` available for download and contains full report |
| 3 | JSON data downloadable | `{run_id}-profiling-data.json` available for download and is valid JSON |
| 4 | Filenames match run ID | All three filenames use the same run ID from the report header |
| 5 | HTML no raw data | HTML report does not display raw data rows (samples suppressed) |
| 6 | JSON schema valid | JSON file contains validation_result, quality_detections, pii_scan, and profiling_statistics keys |

**Fail Indicators:** Any file missing; filename mismatch; raw data visible in HTML; invalid JSON.

---

## Evaluation Fixture Files

The following synthetic files must be created before evaluations are run:

| File | Purpose |
|------|---------|
| eval-fixture-clean-500x12.csv | eval-001: known issues dataset |
| eval-fixture-pii-200x10.csv | eval-002: PII detection dataset |
| edge-empty.csv | eval-003: headers only |
| edge-single-row.csv | eval-003: 1 data row |
| edge-duplicate-cols.csv | eval-003: duplicate column names |
| edge-special-chars.csv | eval-003: special characters |
| edge-not-csv.txt | eval-003: non-CSV text file |

All fixture data is synthetic and anonymized — no real PII.

---

## Constitution CSV Datasets

The three datasets specified in the constitution's V1 Definition of Done (NYC TLC Trip Records, Kaggle Instacart/Dunnhumby, UCI dataset) are validated as **separate end-to-end acceptance tests** after the pipeline is fully implemented. They are not part of the unit evaluation suite, which uses synthetic fixtures for controlled, reproducible testing. The end-to-end tests are documented as a Phase 3 gate.
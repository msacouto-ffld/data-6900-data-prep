# Evaluation Suite: V1 Minimum

**Coverage**: User Stories P1 (1, 2, 3, 4) and P2 (5, 6) | **Format**: Structured .md

---

## Purpose

Six evaluation cases ensuring the transformation pipeline meets the spec's acceptance scenarios and the constitution's edge-case requirements. Each evaluation defines a fixed input set, invocation, expected behavior, and binary pass criteria.

---

## eval-101 — LLM Suggests and Validates Cleaning Transformations (User Story 1)

**Fixed Input Set:**

- Profiling JSON: Synthetic profiling output reporting the following issues in a 500-row × 12-column dataset:
  - 2 columns with special characters in names
  - 1 column 100% missing
  - 1 column with mixed types (int + string)
  - 1 column with 15% missing (numeric)
  - 1 column with 8% missing (categorical)
  - 50 exact duplicate rows
- NL report: Synthetic markdown matching the profiling JSON

**Invocation:** Load outputs → "Clean this dataset."

**Pass Criteria:**

| # | Criterion | Pass Condition |
|---|-----------|----------------|
| 1 | All issues addressed | Transformation plan includes at least one transformation per detected issue |
| 2 | 7-step structure | All transformations mapped to correct pipeline steps |
| 3 | Catalog strategies preferred | All proposed strategies are from the catalog (no custom) for this standard dataset |
| 4 | Parameters present | Required parameters present for each strategy |
| 5 | Review panel runs | Review panel output exists with verdicts for all transformations |
| 6 | At least one challenge | Review panel challenges at least one assumption (per SC-102) |
| 7 | Confidence scores | Every transformation has a fixed confidence score (95, 82, 67, 50, or 35) |
| 8 | Rejection loop works | If any transformation rejected, alternative proposed and re-reviewed |
| 9 | Issue prefix format | Every transformation's `issue` field starts with the detection type |
| 10 | No fabricated issues | No transformations proposed for issues not in the profiling data |

**Fail Indicators:** Missing issues, wrong step assignments, custom strategy for standard issue, missing parameters, no challenge from panel.

---

## eval-102 — Execute Approved Transformations (User Story 2)

**Fixed Input Set:**

- Raw CSV: Synthetic 500-row × 12-column dataset matching eval-101's profiling data
- Pre-approved plan: A fixed DM-106 plan with known transformations (to isolate execution from proposal)

**Invocation:** Execute the pre-approved plan.

**Pass Criteria:**

| # | Criterion | Pass Condition |
|---|-----------|----------------|
| 1 | Output CSV exists | `{run_id}-cleaned.csv` exists and is valid CSV |
| 2 | Row count correct | Rows = 500 - 50 (duplicates) = 450 |
| 3 | Column count correct | Columns = 12 - 1 (all-missing dropped) = 11 |
| 4 | Column names standardized | All column names match snake_case regex `^[a-z_][a-z0-9_]*$` |
| 5 | No missing in imputed columns | Columns targeted for imputation have 0 missing values |
| 6 | Type consistency | Mixed-type column has consistent dtype after coercion |
| 7 | No duplicates | 0 exact duplicate rows in output |
| 8 | No unapproved changes | Columns not in any transformation's `affected_columns` have identical values to input |
| 9 | Determinism | Running the same plan twice produces numerically equivalent CSV output (floating-point tolerance: 1e-10 per cell). Comparison uses `numpy.allclose()` for numeric columns and exact match for non-numeric columns. |
| 10 | Before/after metrics | Step results contain valid metrics_before and metrics_after for each executed step |

**Fail Indicators:** Wrong row/column count, remaining duplicates, unapproved column changes, non-deterministic output.

---

## eval-103 — Generate Transformation Report (User Story 3)

**Fixed Input Set:**

- Step results from eval-102 execution
- Approved plan and review outputs from eval-101

**Invocation:** Generate transformation report.

**Pass Criteria:**

| # | Criterion | Pass Condition |
|---|-----------|----------------|
| 1 | All required sections present | Header, Executive Summary, Dataset Comparison, Transformations Applied, Next Steps, Verification Summary, Pipeline Log Summary |
| 2 | 3-part template | Every transformation entry has What/Why/Impact |
| 3 | Confidence scores | Every transformation shows score and band |
| 4 | Dataset comparison table | Before/after row count, column count, missing cells, duplicate rows |
| 5 | Before/after per transformation | Each transformation shows affected column metrics |
| 6 | High-impact flags | Any threshold exceedance shown with actual value and threshold |
| 7 | Plain language | No undefined acronyms; no unexplained method-specific terms |
| 8 | No raw data values | Report contains no actual data values from the CSV |
| 9 | Next Steps present | Section lists normalization and encoding as Skill B responsibilities |
| 10 | Verification Summary | Section present with PASS or CORRECTIONS APPLIED |
| 11 | Jargon scan passes | scan_jargon returns no undefined terms (or corrections applied) |

**Fail Indicators:** Missing sections, missing what/why/impact, undefined jargon, raw data values.

---

## eval-104 — Download Outputs (User Story 4)

**Fixed Input Set:** Same pipeline run as eval-102/103.

**Invocation:** After report delivery, check downloads.

**Pass Criteria:**

| # | Criterion | Pass Condition |
|---|-----------|----------------|
| 1 | Cleaned CSV downloadable | `{run_id}-cleaned.csv` available and valid |
| 2 | Report downloadable | `{run_id}-transform-report.md` available and contains all sections |
| 3 | Metadata JSON downloadable | `{run_id}-transform-metadata.json` available and valid JSON |
| 4 | Mistake log downloadable | `{run_id}-mistake-log.json` available and valid JSON |
| 5 | Filenames match run ID | All filenames use the same transform run ID |
| 6 | Metadata provenance | JSON contains `produced_by: "skill_a"` and valid `handoff_contract_version` |
| 7 | Metadata counts match | `row_count_after` and `column_count_after` match actual cleaned CSV |
| 8 | PII warnings carried | Metadata `pii_warnings` matches Feature 1's PII scan results |
| 9 | Skipped transformations listed | Metadata `skipped_transformations` lists normalization, encoding with `source: "skill_boundary"` |
| 10 | Mistake log no raw data | Mistake log entries contain no raw data values |

**Fail Indicators:** Any file missing, filename mismatch, provenance missing, counts don't match.

---

## eval-105 — Data Analyst Persona Verification (User Story 5)

**Fixed Input Set:**

- Cleaned CSV from eval-102 with one known intentional issue: `step_results` metrics show expected row count of 450, while the provided cleaned CSV has only 447 rows. The Data Analyst persona receives both the metrics and the final `capture_metrics()` output — the discrepancy between expected (450) and actual (447) is what it should catch.
- Step results showing the expected counts (before the bug)

**Invocation:** Run verify_output on the intentionally flawed output.

**Pass Criteria:**

| # | Criterion | Pass Condition |
|---|-----------|----------------|
| 1 | Discrepancy detected | Persona flags the row count mismatch |
| 2 | Specific description | Discrepancy message identifies the exact count difference |
| 3 | No false positives | On the clean eval-102 output, persona reports PASS with no discrepancies |
| 4 | High-impact acknowledged | Persona acknowledges all high-impact flags from step results |
| 5 | Unapproved change detection | Persona flags if any non-targeted column has changed statistics |

**Fail Indicators:** Bug not caught, false discrepancy on clean output, high-impact flags ignored.

---

## eval-106 — Edge Cases and Special Workflows

**Fixed Input Set:** Five separate scenarios, each tested independently:

| Scenario | Input | Expected Behavior |
|----------|-------|-------------------|
| No-issues dataset | Profiling JSON with all detections `status: "clean"` | Light verification; "no cleaning required" report; original CSV output unchanged |
| Human review escalation | Profiling JSON crafted to produce a step 5 imputation with no consensus (35 score). User input simulated: "Option 1" | Escalation presented with 3 options + perspectives; user choice applied; decision recorded in DM-106 and mistake log |
| High-impact row reduction | Dataset where deduplication removes >10% of rows | High-impact flag in step results and report |
| Dependency-aware skip | User skips step 3 (type coercion); step 5 (imputation) depends on it | Warning issued about downstream dependency; warning in report and mistake log |
| All transformations rejected twice | Review panel rejects all transformations across 2 rounds | All transformations escalated to human review (score = 35 for all) |

**Pass Criteria:**

| # | Criterion | Pass Condition |
|---|-----------|----------------|
| 1 | No-issues path | Light verification runs; report states no cleaning needed; CSV unchanged |
| 2 | Escalation UX | Options presented with perspectives and column context; user choice accepted and applied |
| 3 | High-impact flagged | Flag message includes actual value and threshold |
| 4 | Dependency warning | Warning issued for skipped step with downstream dependencies |
| 5 | Full escalation | All transformations presented to user for decision after max rejection loops |
| 6 | Mistake log captures all | All edge case events recorded in mistake log with correct types |

**Fail Indicators:** No-issues path runs standard pipeline, escalation missing options, dependency warning absent, mistake log incomplete.

---

## Evaluation Fixture Files

| File | Purpose |
|------|---------|
| `eval-profiling-standard.json` | eval-101, 102, 103, 104: standard profiling output with known issues |
| `eval-raw-500x12.csv` | eval-102: synthetic raw CSV matching the profiling data |
| `eval-approved-plan.json` | eval-102: pre-approved DM-106 plan |
| `eval-profiling-clean.json` | eval-106: profiling output with all detections clean |
| `eval-profiling-no-consensus.json` | eval-106: profiling output crafted for consensus failure |
| `eval-profiling-high-dedup.json` | eval-106: profiling output for >10% duplicate rows |
| `eval-cleaned-with-bug.csv` | eval-105: cleaned CSV with intentional row count error |

All fixture data is synthetic and anonymized — no real PII.

---

## Constitution CSV Datasets

The three datasets specified in the constitution's V1 Definition of Done (NYC TLC, Kaggle Instacart/Dunnhumby, UCI) are validated as separate end-to-end acceptance tests after both Skill A features and Skill B are fully implemented. They are not part of the unit evaluation suite, which uses synthetic fixtures for controlled, reproducible testing. The end-to-end tests are documented as a Phase 3 gate.

# Data Profiling & Exploratory Report — Phase 0 Research

**Date**: 2026-04-04 | **Spec**: Feature 001 — Data Profiling | **Status**: Approved

## Purpose

This document identifies all open technical questions that must be resolved before design begins. For each question, it states the options and recommends an answer with rationale. Approved answers become inputs to Phase 1 (data-model.md, quickstart.md, contracts/).

---

## RQ-001 — ydata-profiling Installation Strategy

**Recommendation:** Install ydata-profiling as the first operation in the pipeline, before any other code runs.

**Installation command (Claude.ai sandbox):**

```python
import subprocess
import sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "ydata-profiling", "-q"])
```

Uses `sys.executable` to ensure the correct Python interpreter is targeted. `-q` suppresses normal output; installation errors (non-zero exit code) are caught by `check_call` and surfaced as: "Dependency error: ydata-profiling could not be installed. Please try again in a new session."

**Post-install verification:**

```python
try:
    import ydata_profiling
    print(f"ydata-profiling {ydata_profiling.__version__} installed successfully.")
except ImportError:
    raise RuntimeError("Dependency error: ydata-profiling could not be installed.")
```

**Dependency:** `matplotlib` is a transitive dependency of ydata-profiling and will be available post-install (confirms A12).

---

## RQ-002 — Input Validation Strategy

**Recommendation:** Sequential validation using pre-installed pandas only. Runs before ydata-profiling installation for fast feedback.

| Step | Check | Type | Failure Behavior |
|------|-------|------|-----------------|
| 1 | File exists and is readable | Hard gate | Error: "File not found or not readable." |
| 2 | File extension is `.csv` | Informational | Warning if non-`.csv` extension; proceeds if parsing succeeds in step 3 |
| 3 | File parses via `pd.read_csv()` | Hard gate (FR-002) | Error: "This file is not a valid CSV. Please check the file format and try again." |
| 4 | DataFrame has ≥1 column | Hard gate | Error: "This CSV has no columns. Please upload a file with at least one column and one row of data." |
| 5 | DataFrame has ≥1 row | Hard gate (FR-003) | Error: "This CSV contains headers but no data rows. Please upload a file with at least one row of data." |
| 6 | Cell count > 500,000 | Hard gate | Error: "This dataset exceeds the profiling limit for Claude.ai ({n} cells). Reduce rows or columns and re-upload." |
| 7 | Cell count 100,000–500,000 | Warning | Warning: "This dataset is large ({n} cells). Profiling may be slow or incomplete. Consider uploading a sample." Proceeds. |
| 8 | Single-row CSV (1 row) | Warning (FR-013) | Proceeds; NL report includes statistical limitations section |

**Clarification:** FR-002 ("reject files that are not valid tabular CSVs") is enforced by step 3 — successful `pd.read_csv()` parsing is the hard gate. File extension (step 2) is informational only.

---

## RQ-003 — Data Quality Detection Pipeline

**Recommendation:** Pure pandas checks, independent of ydata-profiling. Run after input validation, before ydata-profiling.

| Detection | FR | Implementation | Notes |
|-----------|----|---------------|-------|
| Duplicate column names | FR-009 | `df.columns.duplicated().any()` | Reports which names are duplicated |
| Special characters | FR-010 | Regex: `r'^[a-zA-Z_][a-zA-Z0-9_]*$'` — flag columns that don't match | Flags spaces, emojis, unicode, leading digits |
| All-missing columns | FR-011 | `df.isnull().all()` | Reports column names with 100% missing |
| Mixed types | FR-012 | `df.apply(lambda col: col.dropna().map(type).nunique() > 1)` | Uses `map` (not deprecated `applymap`); drops NaN before type check to avoid counting NoneType |

**Output format per detection:**

```python
{
    "check": "duplicate_column_names",
    "status": "found",          # or "clean"
    "affected_columns": ["col_a", "col_b"],
    "details": "Columns 'col_a' and 'col_b' have identical names."
}
```

Results passed to the LLM as structured findings for the NL report.

---

## RQ-004 — Chart Generation Strategy

**Recommendation:** 3 inline charts generated via matplotlib after ydata-profiling completes. Charts displayed inline in chat; LLM references them by name.

| Chart | Data Source | Inclusion Rule | Layout |
|-------|-----------|----------------|--------|
| Missing values bar | `df.isnull().mean() * 100` | Omitted if zero missing values | Horizontal bar; sorted descending; only >0% shown |
| Data type distribution bar | `df.dtypes.value_counts()` | Always included | Vertical bar; one bar per dtype category |
| Numeric distribution histograms | `df.select_dtypes(include='number')` | Omitted if no numeric columns | Grid: max 4 columns wide; **capped at top 12 numeric columns by variance**; `bins=30` |

**Histogram cap:** If the dataset has more than 12 numeric columns, only the top 12 by variance are shown. The NL report notes: "Showing distributions for the 12 highest-variance numeric columns out of {n} total."

**File output:** Each chart saved as PNG to sandbox filesystem with naming: `{run_id}-chart-{chart_type}.png` (e.g., `profile-20260402-143022-a3f7-chart-missing.png`).

**matplotlib backend:** `matplotlib.use('Agg')` — non-interactive backend for sandbox execution.

---

## RQ-005 — PII Detection Approach

**Recommendation:** Two-layer hybrid — heuristic pre-scan on column names (Script) + LLM value inspection.

### Layer 1 — Heuristic Pre-Scan (Script)

Uses **word-boundary matching** (not substring) to reduce false positives. Column names are normalized to lowercase and split on common delimiters (`_`, `-`, ` `, `.`) before matching.

| PII Type | Match Tokens (word-boundary) |
|----------|---------------------------|
| Direct — names | `name`, `first_name`, `last_name`, `full_name`, `surname`, `customer_name`, `person` |
| Direct — contact | `email`, `phone`, `telephone`, `mobile`, `cell`, `address`, `street`, `city`, `state`, `country` |
| Direct — identifiers | `ssn`, `social_security`, `passport`, `driver_license`, `national_id`, `license_number` |
| Indirect | `dob`, `date_of_birth`, `birth_date`, `birthday`, `zip`, `zip_code`, `postal_code`, `job_title`, `occupation`, `age`, `gender`, `sex`, `race`, `ethnicity`, `religion` |
| Financial | `account_number`, `account_no`, `credit_card`, `card_number`, `routing_number`, `iban`, `transaction_id`, `bank`, `salary`, `income` |

**Word-boundary logic:** Column name `filename` does not match `name` because `file` is not a delimiter-separated prefix. Column name `first_name` matches because `name` appears as a complete token after splitting on `_`.

### Layer 2 — LLM Value Inspection

The LLM receives the first 5 non-null values per column and analyzes whether values resemble PII patterns (email format, phone number format, SSN format, etc.). This catches PII in columns with non-descriptive names.

**Exception to RQ-007 constraint:** The LLM does inspect sample values from the raw CSV for PII detection. This is the only permitted direct data access — all other NL report content must be sourced from profiling output and script detections.

### Combined Output

**Warning format:**

```
⚠️ PII Warning: Column '{column_name}' may contain {PII_type} PII ({detection_source}).
   Proceed with caution — do not share this data without appropriate safeguards.
```

Where `{detection_source}` is "column name pattern" or "value pattern detected by LLM".

**Privacy safeguard:** The NL report includes column names and PII categories only — never raw PII values.

---

## RQ-006 — Persona Validation Implementation

**Recommendation:** Two-phase LLM call with structured validation checklist.

**Phase 1 (Draft):** LLM generates NL report from profiling data, quality detections, and PII scan.

**Phase 2 (Review):** Data Analyst persona receives:

1. Draft NL report
2. Raw profiling statistics (dict/JSON)
3. Data quality detection results (structured dicts)
4. PII scan results
5. Validation checklist:

| Check | What the Analyst Verifies |
|-------|--------------------------|
| Statistical accuracy | All percentages, counts, and statistics match profiling output |
| Completeness | All major findings represented |
| PII coverage | All flagged columns included |
| No fabrication | No unsupported claims |
| Plain language | FR-007 compliance — no undefined acronyms, no unexplained terms |
| Chart references | Inline charts correctly referenced |

**Output:** Appended to the NL report as the final section:

```markdown
## Verification Summary

**Corrections Made:**
- [list, if any]

**Confirmed Accurate:**
- [list of verified claims]

**Review Status:** PASS / CORRECTIONS APPLIED
```

**Section title:** "Verification Summary" (not "Analyst Review") — user-friendly for Level B audience.

---

## RQ-007 — NL Report Generation Strategy

**Inputs to LLM (Draft generation):**

| Input | Source | Purpose |
|-------|--------|---------|
| ydata-profiling summary statistics | Profiling report object (dict) | Factual basis for all claims |
| Data quality detection results | RQ-003 scripts | FR-009–012 findings |
| PII scan results | RQ-005 heuristic + LLM | FR-008 warnings |
| Chart file references | RQ-004 filenames | So LLM can reference charts by name |
| NL report template | Approved 7-section structure | Structural guide |
| Run metadata | Run ID, filename, timestamp | Report header |

**Key constraint:** The LLM must not analyze the raw CSV directly for the NL report, with one exception: PII value inspection (RQ-005 Layer 2). All statistical claims must be sourced from ydata-profiling output and script-based detections.

**Plain language enforcement (FR-007):**

- Basic statistical terms (mean, median, mode, outlier) — permitted without explanation
- Method-specific terms (z-score, IQR, kurtosis) — explained on first use
- All acronyms — defined on first use
- Every metric — given context (% of rows, column name, before/after)

---

## RQ-008 — Download Mechanism

**Recommendation:** Both files written to sandbox filesystem and presented via Claude.ai's file presentation mechanism.

| File | Format | Filename | Content |
|------|--------|----------|---------|
| HTML profile report | .html | `{run_id}-profile.html` | ydata-profiling output |
| NL summary | .md | `{run_id}-summary.md` | Final NL report (post-verification) |

**Delivery sequence:**

1. NL report delivered inline in chat with inline charts
2. Both files presented for download
3. Follow-up: "Your profiling outputs are ready for download. The HTML report contains the full statistical profile; the markdown file contains the natural language analysis."

---

## Open Questions Deferred to Phase 1

| ID | Question | Deferred To |
|----|----------|-------------|
| D1 | Exact ydata-profiling configuration parameters (minimal mode vs. full) | data-model.md |
| D2 | NL report markdown field order within each section | data-model.md |
| D3 | Exact invocation syntax for user | quickstart.md |
| D4 | Per-script input/output/error contract details | contracts/ |
| D5 | Feature 2 handoff format — what exactly does Feature 2 consume from Feature 1? | data-model.md |
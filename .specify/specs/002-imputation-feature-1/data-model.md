# Data Profiling & Exploratory Report — Phase 1 Data Model

**Date**: 2026-04-04 | **Spec**: Feature 001 — Data Profiling | **Status**: Approved

## Purpose

This document defines all data schemas used by the Data Profiling pipeline. Every field name, type, and required/optional designation is concrete — no placeholders. These schemas are the authoritative source for script contracts, LLM prompt design, and evaluation fixtures.

---

## DM-001 — Raw CSV Input

**Format:** `.csv`
**Encoding:** UTF-8
**Source:** User upload to Claude.ai

**Validation rules (FR-001, FR-002, FR-003):**

| Rule | Enforcement |
|------|------------|
| File is readable | Hard gate |
| File parses via `pd.read_csv()` | Hard gate (FR-002) |
| ≥1 column | Hard gate |
| ≥1 data row | Hard gate (FR-003) |
| Cell count ≤ 500,000 | Hard gate |
| Cell count 100,000–500,000 | Warning — proceeds |
| Single row | Warning (FR-013) — proceeds with statistical limitations note |
| Non-`.csv` extension | Warning — proceeds if parsing succeeds |

**Failure messages:**

- `"File not found or not readable."`
- `"This file is not a valid CSV. Please check the file format and try again."`
- `"This CSV has no columns. Please upload a file with at least one column and one row of data."`
- `"This CSV contains headers but no data rows. Please upload a file with at least one row of data."`
- `"This dataset exceeds the profiling limit for Claude.ai ({n} cells). Reduce rows or columns and re-upload."`

---

## DM-002 — Validation Result (Internal)

**Format:** Python dict (in-memory; not written to disk)
**Produced by:** Input validation script
**Consumed by:** All downstream pipeline steps

```python
{
    "run_id": "string — profile-YYYYMMDD-HHMMSS-XXXX",
    "filename": "string — original uploaded filename",
    "file_path": "string — sandbox path to uploaded file",
    "row_count": "integer",
    "column_count": "integer",
    "cell_count": "integer — row_count × column_count",
    "is_single_row": "boolean",
    "warnings": ["string — list of warning messages issued during validation"],
    "validated_at": "string — ISO 8601 timestamp"
}
```

**Notes:**

- All downstream steps reference `run_id` from this dict
- `warnings` captures file size warnings, single-row warnings, extension warnings
- Not persisted to disk — lives in the Python session for the duration of the pipeline

**Session crash note:** If the pipeline crashes mid-execution, all in-memory state is lost. Users must re-run from the beginning. Documented in quickstart.md.

---

## DM-003 — Data Quality Detections (Internal)

**Format:** Python list of dicts (in-memory)
**Produced by:** Data quality detection scripts (RQ-003)
**Consumed by:** LLM for NL report generation

```python
[
    {
        "check": "string — one of: duplicate_column_names, special_characters, all_missing_columns, mixed_types",
        "status": "string — found | clean",
        "affected_columns": ["string — column names affected"],
        "details": "string — human-readable description of the finding"
    }
]
```

**One entry per check.** Four checks total (FR-009, FR-010, FR-011, FR-012). If a check finds no issues, `status` is `"clean"` and `affected_columns` is empty.

---

## DM-004 — PII Scan Results (Internal)

**Format:** Python list of dicts (in-memory)
**Produced by:** PII heuristic script (Layer 1) + LLM value inspection (Layer 2)
**Consumed by:** LLM for NL report generation

```python
[
    {
        "column_name": "string",
        "pii_type": "string — one of: direct_name, direct_contact, direct_identifier, indirect, financial",
        "pii_category": "string — human-readable (e.g., 'Direct PII — email address')",
        "detection_source": "string — column_name_pattern | value_pattern_llm",
        "confidence": "string — high | medium"
    }
]
```

**Rules:**

- One entry per flagged column. A column may have multiple entries if flagged by both layers.
- `confidence`: `high` for Layer 1 exact token matches; `medium` for Layer 2 LLM-based detection
- Empty list if no PII detected
- Raw data values are **never** included in this structure (FR-016)

---

## DM-005 — ydata-profiling Configuration

**Format:** Python dict passed to `ProfileReport()`
**Purpose:** Controls what ydata-profiling computes

```python
{
    "title": "string — 'Data Profile: {filename}'",
    "minimal": "boolean — True if cell_count > 50,000; False otherwise",
    "explorative": "boolean — False (default; keeps report focused)",
    "correlations": {
        "pearson": {"calculate": True},
        "spearman": {"calculate": False},
        "kendall": {"calculate": False},
        "phi_k": {"calculate": False}
    },
    "missing_diagrams": {
        "bar": True,
        "matrix": False,
        "heatmap": False
    },
    "samples": {
        "head": 0,
        "tail": 0
    }
}
```

**Key decisions:**

- **`minimal=True`** for datasets >50,000 cells — reduces computation time and memory usage in the sandbox
- **`samples.head=0, samples.tail=0`** — prevents raw data values from appearing in the HTML report (FR-016 compliance)
- **Correlations:** Only Pearson enabled for V1 — keeps computation manageable
- **Missing diagrams:** Bar chart only — matrix and heatmap are expensive for large datasets

**Profiling mode tracking:** The pipeline records which mode was used:

```python
"profiling_mode": "string — full | minimal"
```

The NL report header includes: `**Profiling Mode**: {full | minimal}`. If minimal, the report notes: "This dataset was profiled in minimal mode due to its size. Some advanced statistics may be unavailable."

---

## DM-006 — Profiling Statistics (Internal)

**Format:** Python dict (extracted from ydata-profiling report object)
**Produced by:** ydata-profiling pipeline step
**Consumed by:** LLM for NL report; Data Analyst persona for verification

```python
{
    "profiling_mode": "string — full | minimal",
    "dataset": {
        "n_rows": "integer",
        "n_columns": "integer",
        "n_cells": "integer",
        "n_missing_cells": "integer",
        "pct_missing_cells": "float — percentage",
        "n_duplicate_rows": "integer",
        "pct_duplicate_rows": "float — percentage",
        "memory_size": "string — human-readable (e.g., '2.4 MB')",
        "types": {
            "numeric": "integer — count of numeric columns",
            "categorical": "integer — count of categorical columns",
            "datetime": "integer — count of datetime columns",
            "boolean": "integer — count of boolean columns",
            "other": "integer — count of other types"
        }
    },
    "columns": {
        "{column_name}": {
            "type": "string — numeric | categorical | datetime | boolean | other",
            "n_missing": "integer",
            "pct_missing": "float",
            "n_unique": "integer",
            "is_unique": "boolean",
            "mean": "float | null — numeric only",
            "std": "float | null — numeric only",
            "min": "float | null — numeric only",
            "max": "float | null — numeric only",
            "median": "float | null — numeric only",
            "top_values": ["string — top 5 most frequent values (categorical only)"],
            "top_frequencies": ["integer — frequencies of top 5 values"]
        }
    },
    "correlations": {
        "pearson": {
            "{col_a}": {
                "{col_b}": "float — correlation coefficient"
            }
        }
    }
}
```

**Hard constraint on `top_values`:** The LLM prompt must include: "Do not reproduce any values from the `top_values` field in the natural language report. You may reference the number of unique values and frequency patterns, but never include actual data values. This is a non-negotiable privacy rule."

**Privacy note:** `top_values` contains actual data values from categorical columns. This structure is used internally only — it is **never** included in logs or exported files.

---

## DM-007 — Chart Metadata (Internal)

**Format:** Python list of dicts (in-memory)
**Produced by:** Chart generation script
**Consumed by:** LLM for NL report chart references

```python
[
    {
        "chart_type": "string — missing_values | dtype_distribution | numeric_histograms",
        "filename": "string — {run_id}-chart-{chart_type}.png",
        "file_path": "string — sandbox path",
        "included": "boolean — whether chart was generated (conditional inclusion rules)",
        "description": "string — brief description for LLM reference (e.g., 'Bar chart showing percentage of missing values per column')",
        "note": "string | null — e.g., 'Showing top 12 of 45 numeric columns by variance'"
    }
]
```

---

## DM-008 — Natural Language Report (Output)

**Format:** Markdown
**Filename:** `{run_id}-summary.md`
**Delivered:** Inline in chat + available for download

```markdown
# Data Profiling Report

**Run ID**: {run_id}
**File**: {filename}
**Rows**: {n_rows} | **Columns**: {n_columns} | **Cells**: {n_cells}
**Profiling Mode**: {full | minimal}
**Generated**: {timestamp}

---

## Dataset Overview

{Row count, column count, column types breakdown, memory footprint.
 Presented in plain language with context.}

## Key Findings

{Top data quality issues ranked by severity/impact.
 Each finding follows the what/why/impact template:
 - **What**: description of the issue
 - **Why it matters**: potential impact on downstream analysis
 - **Scope**: percentage of rows/columns affected

 Inline charts referenced here by name:
 - "As shown in the missing values chart below, ..."
 - "The data type distribution chart shows ..."}

[Inline chart: missing values bar chart — if applicable]
[Inline chart: data type distribution bar chart]
[Inline chart: numeric distribution histograms — if applicable]

## PII Scan Results

{Either:
 - List of PII warnings per column (⚠️ format from RQ-005), OR
 - "No potential PII was detected in this dataset."}

## Column-Level Summary

{Per-column summary — type, missing %, unique count, notable issues.
 Presented as a markdown table.
 CAPPED at 30 columns by issue severity if dataset has >30 columns.
 Sort order: mixed types > all missing > special chars > duplicate names > high missing % > normal.}

| Column | Type | Missing % | Unique | Issues |
|--------|------|-----------|--------|--------|
| {name} | {type} | {pct}% | {n} | {issues or "None"} |

{If capped: "Showing 30 of {n} columns — see the HTML profile report
 for the complete column-level breakdown."}

## Statistical Limitations

{Only present when applicable:
 - Single-row CSV: "This dataset has only one row — profiling
   statistics such as distributions and correlations are not meaningful."
 - Single-column CSV: "This dataset has only one column — correlation
   analysis is not applicable."
 - Omitted entirely if no limitations apply.}

## Recommendations

{What to address before proceeding to data cleaning (Feature 2).
 Actionable, prioritized list. Each recommendation follows
 the what/why/impact template.

 Priority levels:
 - Critical: Issues that would cause Feature 2 to fail
   (e.g., all-missing columns, duplicate column names, non-parseable types)
 - High: Issues that significantly affect data quality
   (e.g., >50% missing in a column, mixed types)
 - Medium: Issues that affect analysis quality
   (e.g., outliers, low-variance columns, special characters in names)
 - Low: Informational findings
   (e.g., single-column dataset, high cardinality)}

## Verification Summary

**Corrections Made:**
- {list of corrections applied by Data Analyst persona, if any}

**Confirmed Accurate:**
- {list of verified claims}

**Review Status:** PASS / CORRECTIONS APPLIED
```

---

## DM-009 — HTML Profile Report (Output)

**Format:** `.html`
**Filename:** `{run_id}-profile.html`
**Produced by:** ydata-profiling `ProfileReport.to_html()`
**Delivered:** Available for download

**Content:** Full ydata-profiling output — statistical summaries, distributions, correlations, missing value patterns, and visualizations. The `samples` config (DM-005) is set to `head=0, tail=0` to prevent raw data from appearing in the report.

**Not consumed by Feature 2.** The NL report (DM-008) is the handoff artifact.

**Implementation note:** During implementation, verify that `samples={"head": 0, "tail": 0}` fully suppresses raw data display in the ydata-profiling HTML output for the installed version (4.18.1). If any raw data rows appear, add `"sensitive": True` to the ProfileReport configuration to engage ydata-profiling's built-in sensitive data mode.

---

## DM-010 — Feature 2 Handoff (Output)

**Format:** Two artifacts — NL report markdown + structured JSON

**Handoff includes:**

| Artifact | Format | Purpose |
|----------|--------|---------|
| NL report | Markdown (`{run_id}-summary.md`) | Human-readable summary for Feature 2's LLM to consume |
| Structured profiling data | JSON (`{run_id}-profiling-data.json`) | Machine-readable data for Feature 2 scripts — contains DM-003 (quality detections), DM-004 (PII scan), and DM-006 (profiling statistics) |

**JSON handoff schema:**

```python
{
    "run_id": "string",
    "filename": "string",
    "validated_at": "string — ISO 8601",
    "profiling_mode": "string — full | minimal",
    "validation_result": { /* DM-002 */ },
    "quality_detections": [ /* DM-003 */ ],
    "pii_scan": [ /* DM-004 */ ],
    "profiling_statistics": { /* DM-006 */ }
}
```

**What Feature 2 consumes from the NL report:**

- The "Key Findings" section — to understand what data quality issues need cleaning
- The "Column-Level Summary" — to understand column types, missing rates, and issues
- The "Recommendations" section — to prioritize cleaning actions
- The "PII Scan Results" — to know which columns require special handling

**What Feature 2 does not consume:**

- The HTML profile report (DM-009) — this is a user reference artifact
- The inline charts — these are for user comprehension only
- The "Verification Summary" — this is an internal quality check

**Skip-profiling workflow:** If a user attempts to run Feature 2 without first running Feature 1, Feature 2 checks for `{run_id}-profiling-data.json`. If absent, Feature 2 halts with: "No profiling data found. Please run data profiling first — upload your CSV and the system will generate a profiling report before cleaning can begin."
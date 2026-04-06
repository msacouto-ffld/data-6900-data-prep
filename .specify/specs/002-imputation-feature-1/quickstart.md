# Data Profiling & Exploratory Report — Phase 1 Quickstart

**Date**: 2026-04-04 | **Spec**: Feature 001 — Data Profiling | **Status**: Approved

## Purpose

Minimal end-to-end walkthrough of the simplest valid Data Profiling invocation. Shows exactly what a user does and what the system returns at each step.

## Prerequisites

- **A Claude.ai account** with access to the conversation interface
- **A CSV file** to profile — must have headers and at least one row of data
- **No special setup required** — no API keys, no local installation, no configuration

## Step 1 — Upload CSV and Request Profiling

Upload your CSV file using the file attachment button in Claude.ai. Then ask for profiling in natural language. Examples:

```
Profile this dataset and tell me what you find.
```
```
What's the state of this data?
```
```
Analyze this CSV and show me the quality issues.
```

The system recognizes profiling intent from a range of natural language prompts — you don't need to use an exact phrase.

## Step 2 — Dependency Setup

The system installs profiling dependencies. The user sees:

```
📦 Installing profiling dependencies...
✅ ydata-profiling installed successfully.
```

If installation fails:

```
❌ Dependency error: ydata-profiling could not be installed.
   Please try again in a new Claude.ai session.
```

## Step 3 — Input Validation

The system validates the uploaded CSV. The user sees:

```
🔍 Validating your dataset...
✅ File: sales_data.csv — valid CSV
✅ Shape: 1,247 rows × 14 columns (17,458 cells)
✅ File size: within profiling limits
✅ Run ID: profile-20260404-143022-a3f7

All checks passed. Starting profiling...
```

Note: The displayed filename is the original upload name as detected by the system.

If validation fails, the user sees a specific error (see Error Reference below). If warnings are issued:

```
⚠️ This dataset is large (245,000 cells). Profiling may be slow
   or incomplete. Consider uploading a sample for initial profiling.

Proceeding with profiling...
```

## Step 4 — Data Quality Checks

The system runs four data quality checks. The user sees only issues and a clean-checks summary:

```
🔍 Running data quality checks...
⚠️ Column names: 2 columns have special characters
   — "Sales Amount ($)", "Customer Name (Full)"
⚠️ Missing values: 1 column is entirely empty — "notes"
⚠️ Mixed types: 1 column has inconsistent types
   — "zip_code" (mix of integer and string values)
✅ 1 of 4 checks passed with no issues (no duplicate column names)

Data quality checks complete. Running full profiling...
```

If all checks are clean:

```
🔍 Running data quality checks...
✅ All 4 data quality checks passed — no issues found.

Running full profiling...
```

## Step 5 — Profiling Execution

The system runs ydata-profiling. The user sees:

```
📊 Running ydata-profiling (full mode)...
   This may take a moment for larger datasets.
✅ HTML profile report generated.
```

If the dataset triggers minimal mode (>50,000 cells):

```
📊 Running ydata-profiling (minimal mode — dataset is large)...
   Some advanced statistics may be unavailable.
✅ HTML profile report generated.
```

## Step 6 — PII Scan

The system scans for potential personally identifiable information. The user sees:

```
🔒 Scanning for potential PII...
⚠️ PII Warning: Column 'customer_name' may contain Direct PII —
   names (column name pattern). Proceed with caution.
⚠️ PII Warning: Column 'email_address' may contain Direct PII —
   email (column name pattern). Proceed with caution.
⚠️ PII Warning: Column 'zip_code' may contain Indirect PII —
   postal code (column name pattern). Proceed with caution.

PII scan complete. 3 columns flagged.
```

If no PII is detected:

```
🔒 Scanning for potential PII...
✅ No potential PII detected in this dataset.
```

## Step 7 — Chart Generation

The system generates inline visualizations. The user sees:

```
📈 Generating visualizations...
✅ Missing values chart generated
✅ Data type distribution chart generated
✅ Numeric distribution histograms generated (8 numeric columns)
```

If a chart is conditionally omitted:

```
📈 Generating visualizations...
ℹ️ Missing values chart skipped — no missing values found
✅ Data type distribution chart generated
✅ Numeric distribution histograms generated (5 numeric columns)
```

## Step 8 — Report Generation and Verification

The system generates the natural language report and verifies it. The user sees:

```
📝 Analyzing profiling results and generating report...
🔎 Verifying report accuracy...
✅ Verification complete — all statistics confirmed accurate.
```

If corrections are applied:

```
📝 Analyzing profiling results and generating report...
🔎 Verifying report accuracy...
⚠️ 1 correction applied — adjusted missing value percentage
   for column 'region' from 12% to 11.4%.
✅ Verification complete — corrections applied.
```

## Step 9 — Report Delivery

The system delivers the final report inline in the chat with inline charts. A truncated example:

```markdown
# Data Profiling Report

**Run ID**: profile-20260404-143022-a3f7
**File**: sales_data.csv
**Rows**: 1,247 | **Columns**: 14 | **Cells**: 17,458
**Profiling Mode**: full
**Generated**: 2026-04-04T14:31:45Z

---

## Dataset Overview

This dataset contains 1,247 rows across 14 columns. The columns
break down as follows: 8 numeric, 5 categorical, and 1 datetime.
The dataset uses approximately 0.3 MB of memory.

## Key Findings

**1. Entirely Empty Column (Critical)**
- **What**: The column "notes" contains no data — 100% of values
  are missing.
- **Why it matters**: This column provides no analytical value
  and will cause errors in any statistical analysis that includes it.
- **Scope**: 1 of 14 columns (7.1% of all columns).

**2. Mixed Data Types in "zip_code" (High)**
- **What**: The "zip_code" column contains a mix of integer and
  string values (e.g., 10001 vs. "10001-3456").
- **Why it matters**: Mixed types prevent consistent sorting,
  grouping, and joining. Numeric zip codes may lose leading zeros.
- **Scope**: 89 of 1,247 rows (7.1%) contain string-format zip codes.

As shown in the missing values chart below, the "notes" column
stands out with 100% missing values, while most other columns
have less than 5% missing data.

[Missing values bar chart displayed inline]
[Data type distribution bar chart displayed inline]
[Numeric distribution histograms displayed inline]

...
```

*(Report continues with PII Scan Results, Column-Level Summary, Recommendations, and Verification Summary sections.)*

## Step 10 — Download

Immediately after the report, the system presents downloadable files:

```
📥 Your profiling outputs are ready for download:
   • profile-20260404-143022-a3f7-profile.html
     — Full statistical profile (interactive HTML report)
   • profile-20260404-143022-a3f7-summary.md
     — Natural language analysis (the report shown above)
   • profile-20260404-143022-a3f7-profiling-data.json
     — Structured profiling data (for technical users or
       downstream data cleaning tools)

Your profiling is complete. You can now proceed to data cleaning,
or download these files to share with your team.
```

## What to Do Next

- **Proceed to data cleaning**: Ask "Clean this dataset based on the profiling results" to begin Feature 2
- **Download and share**: Use the download links above to save the reports
- **Profile another file**: Upload a new CSV and ask for profiling
- **Ask questions**: Ask follow-up questions about the results — e.g., "Tell me more about the mixed types in zip_code"

## Error Reference

| Error | Cause | What to Do |
|-------|-------|-----------|
| File not found or not readable | Upload failed or file is corrupted | Re-upload the file |
| This file is not a valid CSV | File is not tabular (e.g., image, PDF, JSON) | Convert to CSV format and re-upload |
| No data rows | CSV has headers but no data | Add data rows to the CSV |
| Exceeds profiling limit ({n} cells) | Dataset too large for sandbox | Reduce rows or columns, or upload a sample |
| Dependency error | Sandbox environment issue | Start a new Claude.ai session and try again |
| Profiling failed or incomplete | ydata-profiling encountered an error | Start a new session; try uploading a smaller sample |
| Pipeline crashed mid-execution | Session state lost | Start a new session and re-upload your CSV — the pipeline runs from the beginning |
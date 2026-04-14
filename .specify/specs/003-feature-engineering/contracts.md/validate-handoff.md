# Feature Engineering with Persona Validation — Phase 1 Contracts

**Date**: 2026-04-06 | **Spec**: Feature 003 — Feature Engineering | **Status**: Draft

---

## contracts/validate-handoff.md

### Contract: validate_handoff
**FR(s):** FR-201, FR-202, FR-219 | **Owner:** Script | **Freedom:** Low | **Runtime:** Executed

### Purpose
Validates the uploaded CSV against the Skill A handoff contract. Generates the run ID. Checks for the three-artifact handoff (CSV + transform-report.md + transform-metadata.json). Verifies provenance and contract version when metadata is present. Produces the validation result dict consumed by all downstream steps. This is the first step in the pipeline.

### Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| file_path | string | Claude.ai upload path (cleaned CSV) | Yes |
| metadata_json_path | string | Claude.ai upload path (transform-metadata.json) | Expected (fallback if absent) |
| transformation_report_path | string | Claude.ai upload path (transform-report.md) | Expected (fallback if absent) |

### Outputs

On success: Returns `validation_result` dict (DM-003 schema).

Console output:
```
🔍 Validating input against Skill A handoff contract...
✅ File: {filename} — valid CSV
✅ Shape: {rows} rows × {cols} columns ({cells} cells)
✅ Provenance: produced by Skill A (contract version 1.0)
✅ Column names: snake_case, no duplicates, no all-missing, no exact duplicate rows
✅ Types: consistent within each column
✅ Run ID: {run_id}
ℹ️ Skill A transform metadata: {found | not found — fallback mode}
ℹ️ Skill A transform report: {found | not found}

All checks passed. Starting feature engineering pipeline...
```

### Validation Rules

| Step | Check | Gate Type | Failure Message |
|------|-------|-----------|-----------------|
| 1 | File exists and is readable | Hard gate | "File not found or not readable." |
| 2 | Parses via `pd.read_csv()` | Hard gate | "This file is not a valid CSV." |
| 3 | ≥1 column | Hard gate | "This CSV has no columns." |
| 4 | ≥1 data row | Hard gate | "This CSV contains headers but no data rows." |
| 5 | Cell count ≤ 500,000 | Hard gate | "This dataset exceeds the feature engineering limit ({n} cells)." |
| 6 | Cell count 100,000–500,000 | Warning | "This dataset is large ({n} cells). Feature engineering may be slow." |
| 7 | Provenance (when metadata present) | Hard gate | "Handoff contract violation: this CSV was not produced by Skill A." |
| 8 | Contract version (when metadata present) | Hard gate | "Handoff contract violation: unsupported contract version '{version}'. Skill B requires 1.0." |
| 9 | No duplicate column names | Hard gate | "Handoff contract violation: duplicate column names — {list}." |
| 10 | Column names snake_case + ASCII | Hard gate | "Handoff contract violation: column names not in snake_case — {list}." |
| 11 | No all-missing columns | Hard gate | "Handoff contract violation: column(s) entirely empty — {list}." |
| 12 | No exact duplicate rows | Hard gate | "Handoff contract violation: exact duplicate rows found ({n} rows)." |
| 13 | Consistent types per column | Hard gate | "Handoff contract violation: column '{col}' has mixed types." |
| 14 | Missing values check | Soft gate | If missing values exist and no metadata available: warn but proceed |
| 15 | transform-metadata.json schema | Informational | If present but malformed: warn and fall back to CSV-only mode |
| 16 | transform-report.md readable | Informational | If present but unreadable: warn and proceed without context |

### Error Conditions

- All hard-gate failures halt the pipeline with an actionable message
- Soft-gate warnings are logged in the mistake log and collected in `validation_result["warnings"]`
- Script must not fail silently

### Dependencies

- pandas — pre-installed
- datetime, secrets, json, re, os — standard library

---

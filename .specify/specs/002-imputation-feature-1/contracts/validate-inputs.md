# Contract: validate_input

**FR(s):** FR-001, FR-002, FR-003, FR-013, FR-015 | **Owner:** Script | **Freedom:** Low | **Runtime:** Executed

## Purpose

Validates the user-uploaded CSV, generates a run ID, and produces the validation result dict consumed by all downstream steps. Runs before ydata-profiling installation for fast feedback. Uses only pre-installed pandas.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| file_path | string | Claude.ai upload path | Yes |

## Outputs

On success: Returns `validation_result` dict (DM-002 schema):

```python
{
    "run_id": "profile-YYYYMMDD-HHMMSS-XXXX",
    "filename": "string",
    "file_path": "string",
    "row_count": "integer",
    "column_count": "integer",
    "cell_count": "integer",
    "is_single_row": "boolean",
    "warnings": ["string"],
    "validated_at": "ISO 8601 timestamp"
}
```

On success — console output:

```
🔍 Validating your dataset...
✅ File: {filename} — valid CSV
✅ Shape: {rows} rows × {cols} columns ({cells} cells)
✅ File size: within profiling limits
✅ Run ID: {run_id}

All checks passed. Starting profiling...
```

## Validation Rules

| Step | Check | Type | Failure Message |
|------|-------|------|----------------|
| 1 | File exists and is readable | Hard gate | "File not found or not readable." |
| 2 | File extension is `.csv` | Informational | Warning if non-`.csv`; proceeds if step 3 succeeds |
| 3 | Parses via `pd.read_csv()` | Hard gate (FR-002) | "This file is not a valid CSV. Please check the file format and try again." |
| 4 | ≥1 column | Hard gate | "This CSV has no columns. Please upload a file with at least one column and one row of data." |
| 5 | ≥1 data row | Hard gate (FR-003) | "This CSV contains headers but no data rows. Please upload a file with at least one row of data." |
| 6 | Cell count ≤ 500,000 | Hard gate | "This dataset exceeds the profiling limit for Claude.ai ({n} cells). Reduce rows or columns and re-upload." |
| 7 | Cell count 100,000–500,000 | Warning | "This dataset is large ({n} cells). Profiling may be slow or incomplete. Consider uploading a sample." |
| 8 | Single-row (1 row) | Warning (FR-013) | Appends warning; proceeds; NL report adds Statistical Limitations section |

**Malformed row handling:** `pd.read_csv()` may succeed on files with inconsistent column counts per row (pandas fills missing values with NaN). This counts as a valid CSV — row-level malformation is detected by the data quality checks (FR-011, FR-012) downstream.

## Run ID Generation (FR-015)

```python
import datetime, secrets
now = datetime.datetime.now()
suffix = secrets.token_hex(2)  # 4 hex chars
run_id = f"profile-{now.strftime('%Y%m%d-%H%M%S')}-{suffix}"
```

## Error Conditions

- All validation errors surface as actionable messages to the user
- Script halts on any hard-gate failure — does not produce validation_result
- Warnings are collected in `validation_result["warnings"]` and the pipeline continues

## Dependencies

- `pandas` — pre-installed
- `datetime` — standard library
- `secrets` — standard library
- `os` — standard library
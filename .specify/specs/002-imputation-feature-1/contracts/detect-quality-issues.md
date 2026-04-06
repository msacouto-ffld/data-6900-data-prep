# Contract: detect_quality_issues

**FR(s):** FR-009, FR-010, FR-011, FR-012 | **Owner:** Script | **Freedom:** Low | **Runtime:** Executed

## Purpose

Runs four independent data quality checks using pandas only. Produces structured detection results consumed by the LLM for the NL report. Runs after input validation, before ydata-profiling.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| df | pandas DataFrame | Loaded during validation | Yes |
| validation_result | dict | DM-002 | Yes |

## Outputs

On success: Returns `quality_detections` list (DM-003 schema):

```python
[
    {
        "check": "string",
        "status": "found | clean",
        "affected_columns": ["string"],
        "details": "string"
    }
]
```

On success — console output (issues found):

```
🔍 Running data quality checks...
⚠️ Column names: {n} columns have special characters — {list}
⚠️ Missing values: {n} column(s) entirely empty — {list}
⚠️ Mixed types: {n} column(s) have inconsistent types — {list}
✅ {n} of 4 checks passed with no issues ({clean check names})

Data quality checks complete. Running full profiling...
```

On success — console output (all clean):

```
🔍 Running data quality checks...
✅ All 4 data quality checks passed — no issues found.

Running full profiling...
```

## Detection Rules

| Check | FR | Implementation | Output when found |
|-------|----|---------------|------------------|
| Duplicate column names | FR-009 | `df.columns.duplicated().any()` | Lists duplicated names |
| Special characters | FR-010 | Regex `r'^[a-zA-Z_][a-zA-Z0-9_]*$'` on each column name — flag non-matches | Lists non-conforming column names |
| All-missing columns | FR-011 | `df.isnull().all()` | Lists column names with 100% missing |
| Mixed types | FR-012 | `df.apply(lambda col: col.dropna().map(type).nunique() > 1)` | Lists columns with >1 Python type |

## Error Conditions

| Condition | Message |
|-----------|---------|
| DataFrame is None or empty | "Pipeline error: no DataFrame available for quality checks. Re-run from the beginning." |

This step does not halt the pipeline on detection findings — findings are informational. It only halts on internal errors.

## Dependencies

- `pandas` — pre-installed
- `re` — standard library
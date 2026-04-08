# Contract: load_feature1_outputs

**FR(s)**: FR-101 | **Owner**: Script | **Freedom**: Low | **Runtime**: Executed

---

## Purpose

Loads and validates the Feature 1 outputs (profiling JSON + NL report markdown + original raw CSV). Generates the transformation run ID. This is the first step in the Feature 2 pipeline.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| sandbox filesystem | — | Claude.ai session | Yes |

## Outputs

On success: Returns `run_metadata` (DM-102), `profiling_data` (parsed DM-101 JSON), `nl_report` (string), `raw_df` (pandas DataFrame)

Console output:

```
🔍 Loading profiling results...
✅ Profiling data loaded: {profiling_run_id}
✅ Original CSV loaded: {filename} ({rows} rows × {cols} columns)
✅ Run ID: {transform_run_id}

Ready to analyze and propose transformations.
```

## Logic

1. Glob sandbox for files matching `profile-*-profiling-data.json`
2. If none found → halt: "No profiling data found. Please run data profiling first."
3. If multiple found → use most recent by timestamp; if ambiguous, ask user
4. Load JSON; validate required top-level keys: `run_id`, `validation_result`, `quality_detections`, `pii_scan`, `profiling_statistics`
5. If any key missing → halt: "Profiling data is incomplete or corrupted. Please re-run data profiling."
6. Load NL report markdown (`{profiling_run_id}-summary.md`). If missing → halt with same message
7. Load original raw CSV from `validation_result.file_path`. If missing → halt: "Original CSV not found. Please re-upload and re-run profiling."
8. Generate transform run ID: `transform-YYYYMMDD-HHMMSS-XXXX`
9. Build `run_metadata` (DM-102)

## Error Conditions

| Condition | Message |
|-----------|---------|
| No profiling JSON found | "No profiling data found. Please run data profiling first — upload your CSV and ask for profiling before cleaning can begin." |
| JSON missing required keys | "Profiling data is incomplete or corrupted. Please re-run data profiling." |
| NL report markdown missing | Same as above |
| Raw CSV missing | "Original CSV not found in this session. Please re-upload your CSV and re-run profiling." |

## Dependencies

- pandas (pre-installed)
- json (standard library)
- glob (standard library)
- datetime (standard library)
- secrets (standard library)

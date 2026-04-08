# Contract: deliver_outputs

**FR(s)**: FR-108, FR-114, FR-115 | **Owner**: Script | **Freedom**: Low | **Runtime**: Executed

---

## Purpose

Writes all output files to the sandbox filesystem, displays the report inline with download links, and writes the mistake log.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| final_report_text | string | From scan_jargon | Yes |
| cleaned_df | DataFrame | From execute_transformations | Yes |
| run_metadata | dict | DM-102 | Yes |
| profiling_data | dict | DM-101 JSON | Yes |
| approved_plan | dict | DM-106 | Yes |
| step_results | list of dict | DM-107 | Yes |
| mistake_log | dict | DM-112 (in-memory) | Yes |

## Outputs

Files written to sandbox:

| File | Format | Content |
|------|--------|---------|
| `{transform_run_id}-cleaned.csv` | CSV | Cleaned dataset (already written by execute_transformations) |
| `{transform_run_id}-transform-report.md` | Markdown | Final transformation report |
| `{transform_run_id}-transform-metadata.json` | JSON | DM-110 handoff metadata for Skill B |
| `{transform_run_id}-mistake-log.json` | JSON | DM-112 mistake log |

## Download Presentation

```
📥 Your cleaning outputs are ready for download:
   • {run_id}-cleaned.csv — Cleaned dataset ({rows} rows × {cols} columns)
   • {run_id}-transform-report.md — Transformation report
   • {run_id}-transform-metadata.json — Transformation metadata

A pipeline log ({run_id}-mistake-log.json) is also available
if you need audit details.
```

## Metadata JSON Construction (DM-110)

Builds the handoff metadata from run_metadata, approved_plan, profiling_data PII warnings, and skipped transformations.

The `skipped_transformations` field is populated from two distinct sources:

| Source | Type Value | Example |
|--------|-----------|---------|
| User-skipped (human review) | `user_skipped` | "Missing value imputation for 'revenue' — no consensus, user chose to skip" |
| Skill A/B boundary deferrals | `skill_boundary` | "Normalization — outside Skill A scope, recommended for Skill B" |

Each entry includes a `source` field: `"user_skipped"` or `"skill_boundary"`.

## Mistake Log Writing

Written via `try/finally` — persisted even on pipeline error:

```python
try:
    # ... pipeline execution ...
finally:
    write_mistake_log(mistake_log, transform_run_id)
```

## Error Conditions

| Condition | Message |
|-----------|---------|
| File write fails | "Output error: could not save {filename}. The report has been delivered inline — please copy it manually." |

File write failure is non-blocking for inline delivery.

## Dependencies

- json (standard library)
- pandas
- Claude.ai file presentation mechanism

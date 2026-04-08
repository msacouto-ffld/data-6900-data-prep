# Contract: collect_mistake_log

**FR(s)**: FR-117, FR-118 | **Owner**: Script | **Freedom**: Low | **Runtime**: Executed (throughout pipeline)

---

## Purpose

Collects mistake log entries in memory throughout pipeline execution. Written to JSON file at completion or on error.

## Inputs

Events from all pipeline steps (passed as function calls throughout execution).

## Outputs

In-memory `mistake_log` dict (DM-112 schema), written to `{transform_run_id}-mistake-log.json` at pipeline end.

## Collection API

```python
def log_entry(mistake_log, entry_type, step, transformation_type,
              description, resolution, affected_columns=None,
              confidence_score=None):
    mistake_log["entries"].append({
        "type": entry_type,
        "step": step,
        "transformation_type": transformation_type,
        "description": description,
        "resolution": resolution,
        "affected_columns": affected_columns or [],
        "confidence_score": confidence_score
    })
```

## Entry Types

| Type | When Recorded |
|------|--------------|
| `persona_rejection` | Review panel rejects a transformation |
| `execution_error` | Step function raises exception |
| `edge_case_warning` | Edge case detected (no-issues, high-impact, etc.) |
| `consensus_failure` | Score = 35; human review escalated |
| `high_impact_flag` | Threshold exceeded |
| `human_review_decision` | User chose option, skipped, or provided guidance |

## Writing (try/finally)

```python
try:
    # ... pipeline execution ...
finally:
    write_mistake_log(mistake_log, transform_run_id)
```

Persisted even if the pipeline halts on an execution error.

## Privacy

- `affected_columns` contains column names only — never raw data values
- `description` and `resolution` use generic descriptions, not data samples

## Dependencies

- json (standard library)

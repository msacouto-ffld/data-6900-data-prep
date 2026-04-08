# Contract: verify_output

**FR(s)**: FR-103 (Test), FR-110 | **Owner**: LLM | **Freedom**: High | **Runtime**: LLM-executed

---

## Purpose

The Data Analyst persona reviews the cleaned output against the original CSV and the approved plan. Checks for unintended side effects, metric consistency, and unapproved changes. This is the "Test" step of the Verification Ritual.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| profiling_data | dict | DM-101 JSON — original CSV stats | Yes |
| step_results | list of dict | DM-107 — from execute_transformations | Yes |
| approved_plan | dict | DM-106 | Yes |
| final_metrics | dict | capture_metrics() on cleaned_df | Yes |
| high_impact_flags | list of dict | Collected from all step_results | Yes |

## Outputs

Returns `verification_result`:

```python
{
    "status": "PASS | CORRECTIONS_APPLIED | DISCREPANCY_FOUND",
    "corrections": ["string — list of corrections, or empty"],
    "confirmed": ["string — list of verified claims"],
    "discrepancies": ["string — list of issues found, or empty"]
}
```

Console output:

```
🔎 Verifying transformations...
{✅ per check}

Verification complete — all checks passed.
```

## Verification Checklist

| Check | What the Analyst Verifies |
|-------|--------------------------|
| Row count consistency | Final row count matches expected count after all approved removals |
| Column count consistency | Final column count matches expected count after drops |
| No unapproved changes | Columns not targeted by any transformation have identical statistics |
| Transformation accuracy | Each transformation's before/after metrics are consistent with strategy |
| No new missing values | Transformations did not introduce unexpected NaN values |
| No new duplicates | Transformations did not introduce duplicate rows |
| High-impact review | Each high-impact flag is acknowledged and justified |
| Type consistency | All columns have the expected dtype after transformation |

## Failure Handling

If `status == "DISCREPANCY_FOUND"`, the pipeline does not halt — it flags the discrepancy to the user in the report and inline: "⚠️ Verification found a discrepancy: {description}. Please review the transformation report and consider re-running the pipeline."

## Error Conditions

| Condition | Message |
|-----------|---------|
| LLM fails to produce verification | "Verification failed. Delivering unverified report with disclaimer." |

If verification fails entirely, the report is delivered with a disclaimer: "⚠️ This report could not be independently verified. Please cross-check against the profiling report."

## Dependencies

- LLM (Claude 4.5 Sonnet) — invoked with Data Analyst persona system prompt

# Feature Engineering with Persona Validation — Phase 1 Contracts

**Date**: 2026-04-06 | **Spec**: Feature 003 — Feature Engineering | **Status**: Draft

---

### Contract: generate_dataset_summary
**FR(s):** Supports FR-203, FR-204 | **Owner:** Script | **Freedom:** Low | **Runtime:** Executed

### Purpose
Produces the structured dataset summary (DM-004) that every LLM call receives. The LLM does not analyze the raw CSV directly — it works from this summary. Runs after validation and PII scan.

### Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| df | pandas DataFrame | Loaded during validation | Yes |
| validation_result | dict | DM-003 | Yes |

### Outputs

On success: Returns `dataset_summary` dict (DM-004 schema).

No console output — this is an internal step.

### Logic

1. For each column: compute dtype, missing count/percentage, unique count, is_unique flag
2. For numeric columns: compute mean, std, min, max, median
3. For each column: extract up to 5 non-null sample values via `df[col].dropna().head(5).tolist()`
4. For PII-flagged columns: replace sample_values with `["[PII — values hidden]"]`
5. Attach Skill A transformation report content as `skill_a_context` (string) if available
6. Attach Skill A metadata content as `skill_a_metadata` (dict) if available — provides column transformation history and skipped transformations to inform feature suggestions

### Error Conditions

| Condition | Message |
|-----------|---------|
| DataFrame is empty | "Pipeline error: no data available for summary generation." |

### Dependencies

- pandas — pre-installed
- numpy — pre-installed

---

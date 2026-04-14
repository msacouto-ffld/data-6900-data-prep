# Feature Engineering with Persona Validation — Phase 1 Contracts

**Date**: 2026-04-06 | **Spec**: Feature 003 — Feature Engineering | **Status**: Draft

---

### Contract: scan_pii
**FR(s):** Constitution PII guardrail (spec gap — added) | **Owner:** Script + LLM | **Freedom:** Medium | **Runtime:** Executed

### Purpose
Checks for PII before feature engineering begins. If transform-metadata.json is available, reads PII flags from its `pii_warnings` field (carried forward by Skill A from Feature 1). If not, runs a lightweight column-name heuristic scan. Produces PII flags consumed by the dataset summary and all LLM calls.

### Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| df | pandas DataFrame | Loaded during validation | Yes |
| validation_result | dict | DM-003 | Yes |

### Outputs

On success: Populates `validation_result["pii_flags"]` (already defined in DM-003).

Console output (from Skill A metadata):
```
🔒 PII scan: loaded {n} flags from Skill A transform metadata
⚠️ Column '{col}' — {PII_type} PII ({category})
...
The LLM will note these columns when proposing features.
```

Console output (heuristic scan):
```
🔒 Running PII scan (heuristic — column names only)...
⚠️ Column '{col}' may contain {PII_type} PII — {category}.
   Consider excluding this column from feature engineering.
...
✅ {n} of {total} columns clear.
```

Console output (no PII):
```
🔒 PII scan complete.
✅ No potential PII detected in this dataset.
```

### Logic

1. Check if `validation_result["has_metadata_json"]` is True
2. If yes: read `pii_warnings` array from transform-metadata.json, populate `pii_flags`
3. If no: run heuristic column-name scan using word-boundary matching against token list (defined in RQ-002)
4. Log all PII warnings to mistake log

### Error Conditions

| Condition | Message |
|-----------|---------|
| transform-metadata.json has invalid pii_warnings schema | "Warning: could not read PII flags from Skill A metadata. Running heuristic scan instead." |

PII scan does not halt the pipeline — findings are warnings only (V1 behavior).

### Dependencies

- pandas — pre-installed
- re — standard library
- json — standard library

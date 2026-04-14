# Feature Engineering with Persona Validation — Phase 1 Contracts

**Date**: 2026-04-06 | **Spec**: Feature 003 — Feature Engineering | **Status**: Draft

---

### Contract: generate_dictionary
**FR(s):** FR-217, FR-223 | **Owner:** LLM | **Freedom:** Medium | **Runtime:** LLM-executed

### Purpose
Auto-generates the data dictionary (DM-011) documenting every engineered feature. A data scientist should be able to read any entry and understand the feature completely without referring to other documents (SC-209).

### Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| approved_features | list | DM-007 | Yes |
| engineered_df | pandas DataFrame | Post-transformation | Yes |

### Outputs

Returns `data_dictionary` string (markdown following DM-011 template).

Console output:
```
📝 Generating data dictionary...
✅ Data dictionary generated.
```

### LLM Prompt Constraints

- **Template enforcement:** "Follow the DM-011 template exactly."
- **Self-contained entries:** "Each feature entry must be understandable on its own. A reader should never need to refer to the transformation report or original dataset."
- **Required fields per feature:** Feature name (with `feat_` prefix), plain-language description, data type, source column(s), transformation method, value range, missing value handling, notes.
- **Plain language:** "Explain all technical terms. A data scientist who has never seen this dataset should understand every entry."
- **No raw data values:** "Do not include actual data values — use descriptions of ranges and patterns."

### Error Conditions

| Condition | Message |
|-----------|---------|
| LLM fails to generate dictionary | Retry once. If fails: "Dictionary generation failed. Feature details available in transformation report." |

### Dependencies

- LLM (Claude 4.5 Sonnet)

---

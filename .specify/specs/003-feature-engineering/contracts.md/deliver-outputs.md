# Feature Engineering with Persona Validation — Phase 1 Contracts

**Date**: 2026-04-06 | **Spec**: Feature 003 — Feature Engineering | **Status**: Draft

---
### Contract: deliver_outputs
**FR(s):** FR-218 | **Owner:** Script | **Freedom:** Low | **Runtime:** Executed

### Purpose
Writes all output files to the sandbox filesystem, displays the transformation report and data dictionary inline in chat, and presents files for download.

### Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| engineered_df | pandas DataFrame | Post-transformation | Yes |
| transformation_report | string | From generate_report | Yes |
| data_dictionary | string | From generate_dictionary | Yes |
| validation_result | dict | DM-003 | Yes |
| mistake_log_path | string | Path to running mistake log | Yes |

### Outputs

Files written to sandbox:

| File | Format | Filename |
|------|--------|----------|
| Feature-engineered CSV | .csv | `{run_id}-engineered.csv` |
| Transformation report | .md | `{run_id}-transformation-report.md` |
| Data dictionary | .md | `{run_id}-data-dictionary.md` |
| Mistake log | .md | `{run_id}-mistake-log.md` (already written throughout run) |

**Inline delivery:**
1. Transformation report (truncated if >10 features)
2. Data dictionary

**Download presentation (3 primary files):**
```
📥 Your feature engineering outputs are ready:
   • {run_id}-engineered.csv
     — Feature-engineered dataset ({original} original + {new} new columns)
   • {run_id}-transformation-report.md
     — Full transformation report with all feature details
   • {run_id}-data-dictionary.md
     — Data dictionary for all engineered features

Engineered columns are prefixed with 'feat_' — use
df.filter(like='feat_') to select them.
```

**Mistake log (always shown):**
```
📋 Mistake log for this run:
   • {run_id}-mistake-log.md
```
The mistake log is always presented — it is the complete operational record of the run, including routine persona rejections, warnings, and any errors. This is what the PM uses to identify recurring patterns.

### Error Conditions

| Condition | Message |
|-----------|---------|
| CSV write fails | "Output error: could not save CSV. Please copy the data from the inline report." |
| Report/dictionary write fails | "Output error: could not save {file}. The content has been delivered inline above." |

File write failures are non-blocking for inline delivery.

### Dependencies

- pandas — for CSV export
- json — standard library
- Claude.ai file presentation mechanism

---

# Contract: verify_report

**FR(s):** Constitution — "AI as Overconfident Intern" verification ritual | **Owner:** LLM (Data Analyst persona) | **Freedom:** Medium | **Runtime:** LLM-executed

## Purpose

Phase 2 of the persona validation loop. The Data Analyst persona reviews the draft NL report against the raw profiling data, applying a structured validation checklist. Produces the Verification Summary section and corrects any errors. The output is the final NL report.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| draft_nl_report | string (markdown) | From generate_nl_report | Yes |
| profiling_statistics | dict | DM-006 | Yes |
| quality_detections | list of dicts | DM-003 | Yes |
| pii_scan | list of dicts | DM-004 | Yes |
| chart_metadata | list of dicts | DM-007 | Yes |

## Outputs

Returns `final_nl_report` — the draft with corrections applied and the Verification Summary section appended.

Console output (no corrections):

```
🔎 Verifying report accuracy...
✅ Verification complete — all statistics confirmed accurate.
```

Console output (corrections applied):

```
🔎 Verifying report accuracy...
⚠️ {n} correction(s) applied — {brief description}.
✅ Verification complete — corrections applied.
```

## Validation Checklist

The Data Analyst persona checks:

| Check | What Is Verified |
|-------|-----------------|
| Statistical accuracy | All percentages, counts, and statistics in the NL report match `profiling_statistics` |
| Completeness | All major findings from `quality_detections` and `profiling_statistics` are represented |
| PII coverage | All entries in `pii_scan` with `status: "found"` are included in PII Scan Results |
| No fabrication | No claims in the report are unsupported by the input data |
| Plain language | FR-007 compliance — no undefined acronyms, no unexplained method-specific terms |
| Chart references | Charts referenced in the report match `chart_metadata` where `included: true` |
| Privacy | No raw data values reproduced from `top_values` or any other source |

## Verification Summary Output

Appended as the final section of the NL report:

```markdown
## Verification Summary

**Corrections Made:**
- {list of specific corrections, or "None"}

**Confirmed Accurate:**
- {list of key verified claims}

**Review Status:** PASS / CORRECTIONS APPLIED
```

## Error Conditions

| Condition | Message |
|-----------|---------|
| Persona fails to produce a review | "Verification failed. Delivering unverified report with disclaimer." |

If verification fails entirely, the pipeline delivers the draft report with a disclaimer: "⚠️ This report could not be independently verified. Please cross-check statistics against the HTML profile report."

## Dependencies

- LLM (Claude 4.5 Sonnet) — invoked with Data Analyst persona system prompt
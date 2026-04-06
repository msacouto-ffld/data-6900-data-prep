# Contract: generate_nl_report

**FR(s):** FR-005, FR-006, FR-007 | **Owner:** LLM | **Freedom:** High | **Runtime:** LLM-executed

## Purpose

The LLM generates a draft natural language report following the 7-section template (DM-008). This is Phase 1 of the two-phase persona validation loop. The draft is not shown to the user — it is passed to the Data Analyst persona for verification.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| profiling_statistics | dict | DM-006 — from run_profiling | Yes |
| quality_detections | list of dicts | DM-003 — from detect_quality_issues | Yes |
| pii_scan | list of dicts | DM-004 — from scan_pii | Yes |
| chart_metadata | list of dicts | DM-007 — from generate_charts | Yes |
| validation_result | dict | DM-002 — from validate_input | Yes |

## Outputs

Returns `draft_nl_report` — a markdown string following the DM-008 template (all 7 sections except Verification Summary, which is added by the persona step).

Console output:

```
📝 Analyzing profiling results and generating report...
```

## LLM Prompt Constraints

The LLM system prompt must include:

1. **Template enforcement:** "Follow the 7-section report template exactly. Do not add, remove, or reorder sections."
2. **Data sourcing:** "All statistical claims must be sourced from the profiling_statistics dict. Do not analyze the raw CSV directly. The only exception is PII value inspection, which has already been completed."
3. **Privacy rule:** "Do not reproduce any values from the `top_values` field. You may reference the number of unique values and frequency patterns, but never include actual data values. This is non-negotiable."
4. **Plain language (FR-007):** "Write for a non-technical business user. Basic statistical terms (mean, median, mode, outlier) are permitted without explanation. Method-specific terms (z-score, IQR, kurtosis) must be explained on first use. All acronyms must be defined on first use. Every metric must include context (percentage of rows affected, column name)."
5. **What/why/impact:** "Every finding in Key Findings and Recommendations must follow the template: What was found → Why it matters → Scope of impact."
6. **Chart references:** "Reference inline charts by name where relevant. Only reference charts where `included` is `true` in chart_metadata."
7. **No fabrication:** "Do not report issues that are not present in the data. If the data is clean, say so."
8. **Column-Level Summary cap:** "If the dataset has more than 30 columns, show the top 30 by issue severity (mixed types > all missing > special chars > duplicate names > high missing % > normal). Note the cap."
9. **Recommendation prioritization:** "Prioritize recommendations as: Critical (would cause Feature 2 to fail) > High (significantly affects data quality) > Medium (affects analysis quality) > Low (informational)."

## Token Budget Estimate

- Input: ~2,000–5,000 tokens (profiling stats + quality detections + PII scan + chart metadata + template + constraints)
- Output: ~1,500–3,000 tokens (full 7-section report)
- Total per call: ~3,500–8,000 tokens

This is a single LLM call. Cost and latency are proportional to dataset complexity (number of columns, number of issues found).

## Error Conditions

| Condition | Message |
|-----------|---------|
| LLM fails to produce a report | "Report generation failed. Please try again." |
| Report does not contain all required sections | Caught by verification step — triggers correction |

## Dependencies

- LLM (Claude 4.5 Sonnet)
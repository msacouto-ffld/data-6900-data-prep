# Contract: generate_report

**FR(s)**: FR-109, FR-110, FR-111, FR-112, FR-113, FR-119 | **Owner**: LLM | **Freedom**: High | **Runtime**: LLM-executed

---

## Purpose

Generates the transformation report (markdown) following the DM-109 template. Includes 3-part justification for every transformation, before/after comparisons, confidence scores, rejections, high-impact flags, and the verification summary.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| step_results | list of dict | DM-107 | Yes |
| approved_plan | dict | DM-106 | Yes |
| review_outputs | list of dict | DM-105 (all rounds) | Yes |
| verification_result | dict | From verify_output | Yes |
| run_metadata | dict | DM-102 | Yes |
| profiling_data | dict | DM-101 JSON | Yes |
| high_impact_flags | list of dict | Collected from step_results | Yes |

## Outputs

Returns `report_text` (markdown string following DM-109 template).

Console output:

```
📝 Generating transformation report...
```

## LLM Prompt Constraints

1. Follow DM-109 template exactly — do not add, remove, or reorder sections
2. All metrics from script-captured data (step_results) — do not compute or estimate
3. Every transformation: 3-part what/why/impact template
4. Plain language (FR-119): basic stats OK; method-specific terms explained on first use; all acronyms defined
5. No raw data values in the report (FR-118)
6. High-impact flags include threshold context
7. Omit empty sections (Rejected, Skipped, High-Impact Summary) if no content
8. Next Steps section references Skill A/B boundary — lists normalization, encoding as Skill B responsibilities
9. Verification Summary from verify_output appended as-is
10. Pipeline Log Summary: count entries by type from the in-memory mistake log

## Error Conditions

| Condition | Message |
|-----------|---------|
| LLM fails to produce report | "Report generation failed. Please try again." |
| Report missing required sections | Retry once; if still incomplete, deliver partial report with disclaimer |

## Dependencies

- LLM (Claude 4.5 Sonnet)
